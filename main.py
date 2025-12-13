import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import json
import random
import string
from dataclasses import dataclass, field
import uuid
import os
import base64
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8534738281:AAGrXV_OEEKdP1hEGKWNTzD1WzStkF6d2Ys")
PORT = int(os.getenv("PORT", 5000))
# Добавьте URL вашего сайта
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://cashapp-platform.onrender.com/")  # <- Ваш сайт
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота с правильными параметрами
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== ДАТАКЛАССЫ ==========
@dataclass
class SiteConfig:
    """Конфигурация сайта"""
    site_id: str
    name: str
    description: str
    theme: str = "cashapp_pro"
    port: int = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    accounts: List[Dict] = field(default_factory=list)
    logo_image: str = None
    ogran_active: bool = False
    ogran_required_accounts: int = 0
    ogran_current_count: int = 0
    
    def to_dict(self):
        return {
            "site_id": self.site_id,
            "name": self.name,
            "description": self.description,
            "theme": self.theme,
            "port": self.port,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%d.%m.%Y %H:%M"),
            "accounts_count": len(self.accounts),
            "logo_image": self.logo_image,
            "ogran_active": self.ogran_active,
            "ogran_required_accounts": self.ogran_required_accounts,
            "ogran_current_count": self.ogran_current_count
        }

# ========== МЕНЕДЖЕР САЙТОВ ==========
class SiteManager:
    def __init__(self):
        self.sites: Dict[str, SiteConfig] = {}
        self.next_port = 5000
        self.load_templates()
        self.default_logo_path = "aa9lldp1y.webp"
        
    def load_templates(self):
        """Загружаем шаблоны"""
        self.html_templates = {
            "cashapp_pro": self.get_cashapp_pro_template(),
            "landing": self.get_landing_page()
        }
        
    def create_site(self, name: str, description: str) -> SiteConfig:
        """Создание нового сайта"""
        site_id = str(uuid.uuid4())[:8]
        port = self.next_port
        self.next_port += 1
        
        # Автоматически загружаем логотип
        logo_image = self.load_default_logo()
        
        site = SiteConfig(
            site_id=site_id,
            name=name,
            description=description,
            theme="cashapp_pro",
            port=port,
            logo_image=logo_image,
            ogran_active=False,
            ogran_required_accounts=0,
            ogran_current_count=0
        )
        
        self.sites[site_id] = site
        self.save_site_html(site)
        
        # Сохраняем в JSON файл
        self.save_to_json()
        
        return site
    
    def load_default_logo(self) -> str:
        """Загружаем стандартный логотип"""
        try:
            if os.path.exists(self.default_logo_path):
                with open(self.default_logo_path, 'rb') as f:
                    image_data = f.read()
                
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                if self.default_logo_path.lower().endswith('.webp'):
                    mime_type = 'image/webp'
                elif self.default_logo_path.lower().endswith('.png'):
                    mime_type = 'image/png'
                elif self.default_logo_path.lower().endswith('.jpg') or self.default_logo_path.lower().endswith('.jpeg'):
                    mime_type = 'image/jpeg'
                else:
                    mime_type = 'image/webp'
                
                return f"data:{mime_type};base64,{base64_image}"
        except Exception as e:
            logger.error(f"Ошибка загрузки логотипа: {e}")
        
        return None
    
    def save_site_html(self, site: SiteConfig):
        """Сохраняем HTML файл для сайта"""
        html_content = self.generate_html(site)
        
        os.makedirs("sites", exist_ok=True)
        
        filename = f"sites/site_{site.site_id}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Обновлен сайт {site.name} (файл: {filename})")
        return filename
    
    def generate_html(self, site: SiteConfig) -> str:
        """Генерация HTML для сайта"""
        template = self.html_templates.get("cashapp_pro")
        
        # Подставляем данные сайта
        html = template.replace("{{SITE_NAME}}", site.name)
        html = html.replace("{{SITE_DESCRIPTION}}", site.description)
        html = html.replace("{{SITE_ID}}", site.site_id)
        html = html.replace("{{PORT}}", str(site.port))
        
        # Логотип
        logo_html = '''<div class="logo-default">
            <svg viewBox="0 0 24 24" fill="#00D632">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
        </div>'''
        if site.logo_image:
            logo_html = f'<img src="{site.logo_image}" class="site-logo" alt="CashApp Logo">'
        
        html = html.replace("{{LOGO}}", logo_html)
        
        # Генерируем аккаунты
        accounts_html = ""
        for i, acc in enumerate(site.accounts, 1):
            status = acc.get("status", "pending")
            status_class = f"status-{status}"
            
            tags_html = ""
            tags = acc.get("tags", [])
            if tags:
                tags_html = '<div class="tags-container">'
                for tag in tags[:3]:
                    if "verified" in tag.lower():
                        tag_class = "tag-success"
                    elif "premium" in tag.lower():
                        tag_class = "tag-premium"
                    elif "2fa" in tag.lower():
                        tag_class = "tag-info"
                    else:
                        tag_class = "tag-default"
                    
                    tags_html += f'<span class="tag {tag_class}">{tag}</span>'
                if len(tags) > 3:
                    tags_html += f'<span class="tag tag-more">+{len(tags)-3}</span>'
                tags_html += '</div>'
            
            login_info = acc.get("email") or acc.get("phone") or "N/A"
            username = login_info.split('@')[0] if '@' in login_info else login_info
            
            accounts_html += f'''
            <div class="account-card">
                <div class="account-header">
                    <div class="account-meta">
                        <span class="account-id">#{i}</span>
                        <div class="account-status {status_class}">
                            <span class="status-dot"></span>
                            <span class="status-text">{status.upper()}</span>
                        </div>
                    </div>
                    <div class="account-time">{acc.get("added_time", datetime.now().strftime("%H:%M"))}</div>
                </div>
                
                <div class="account-body">
                    <div class="account-avatar">
                        <div class="avatar-circle">
                            {username[0].upper() if username else "U"}
                        </div>
                    </div>
                    <div class="account-info">
                        <h3 class="account-name">{username[:20]}</h3>
                        <p class="account-email">{login_info[:30]}{'...' if len(login_info) > 30 else ''}</p>
                    </div>
                </div>
                
                {tags_html}
            </div>
            '''
        
        html = html.replace("{{ACCOUNTS}}", accounts_html)
        
        # Статистика
        stats = self.calculate_stats(site.accounts)
        html = html.replace("{{TOTAL_ACCOUNTS}}", str(stats["total"]))
        html = html.replace("{{PROCESSING_COUNT}}", str(stats["processing"]))
        html = html.replace("{{VALID_COUNT}}", str(stats["valid"]))
        html = html.replace("{{PENDING_COUNT}}", str(stats["pending"]))
        html = html.replace("{{BANNED_COUNT}}", str(stats["banned"]))
        html = html.replace("{{TAGS_COUNT}}", str(stats["tags_count"]))
        html = html.replace("{{UPDATE_TIME}}", datetime.now().strftime("%H:%M:%S"))
        
        # Данные для Ограна
        html = html.replace("{{OGRAN_ACTIVE}}", "true" if site.ogran_active else "false")
        html = html.replace("{{OGRAN_REQUIRED}}", str(site.ogran_required_accounts))
        html = html.replace("{{OGRAN_CURRENT}}", str(site.ogran_current_count))
        html = html.replace("{{OGRAN_REMAINING}}", str(max(0, site.ogran_required_accounts - site.ogran_current_count)))
        
        return html
    
    def calculate_stats(self, accounts: List[Dict]) -> Dict:
        """Рассчитываем статистику"""
        stats = {
            "total": len(accounts),
            "valid": 0,
            "processing": 0,
            "pending": 0,
            "banned": 0,
            "tags_count": 0,
        }
        
        for acc in accounts:
            status = acc.get("status", "pending")
            if status in stats:
                stats[status] += 1
            
            if acc.get("tags"):
                stats["tags_count"] += len(acc.get("tags"))
        
        return stats
    
    def add_accounts_to_site(self, site_id: str, accounts_data: List[Dict]):
        """Добавляем аккаунты на сайт"""
        if site_id not in self.sites:
            return False
        
        site = self.sites[site_id]
        
        if site.ogran_active and site.ogran_current_count < site.ogran_required_accounts:
            new_accounts_count = len(accounts_data)
            site.ogran_current_count = min(
                site.ogran_required_accounts,
                site.ogran_current_count + new_accounts_count
            )
        
        site.accounts.extend(accounts_data)
        
        self.save_site_html(site)
        self.save_to_json()
        
        return True
    
    def update_account_status(self, site_id: str, account_index: int, status: str):
        """Обновление статуса аккаунта"""
        if site_id not in self.sites:
            return False
        
        site = self.sites[site_id]
        if 0 <= account_index < len(site.accounts):
            site.accounts[account_index]["status"] = status
            
            self.save_site_html(site)
            self.save_to_json()
            return True
        
        return False
    
    def add_tag_to_account(self, site_id: str, account_index: int, tag: str):
        """Добавление тега к аккаунту"""
        if site_id not in self.sites:
            return False
        
        site = self.sites[site_id]
        if 0 <= account_index < len(site.accounts):
            if "tags" not in site.accounts[account_index]:
                site.accounts[account_index]["tags"] = []
            
            if tag not in site.accounts[account_index]["tags"]:
                site.accounts[account_index]["tags"].append(tag)
                self.save_site_html(site)
                self.save_to_json()
                return True
        
        return False
    
    def activate_ogran(self, site_id: str, required_accounts: int):
        """Активация Ограна на сайте"""
        if site_id not in self.sites:
            return False
        
        site = self.sites[site_id]
        site.ogran_active = True
        site.ogran_required_accounts = required_accounts
        site.ogran_current_count = 0
        
        self.save_site_html(site)
        self.save_to_json()
        
        return True
    
    def deactivate_ogran(self, site_id: str):
        """Деактивация Ограна на сайте"""
        if site_id not in self.sites:
            return False
        
        site = self.sites[site_id]
        site.ogran_active = False
        site.ogran_required_accounts = 0
        site.ogran_current_count = 0
        
        self.save_site_html(site)
        self.save_to_json()
        
        return True
    
    def check_ogran_completion(self, site_id: str) -> bool:
        """Проверка выполнения условий Ограна"""
        if site_id not in self.sites:
            return False
        
        site = self.sites[site_id]
        if not site.ogran_active:
            return True
        
        return site.ogran_current_count >= site.ogran_required_accounts
    
    def get_ogran_status(self, site_id: str) -> Dict:
        """Получить статус Ограна"""
        if site_id not in self.sites:
            return None
        
        site = self.sites[site_id]
        return {
            "active": site.ogran_active,
            "required": site.ogran_required_accounts,
            "current": site.ogran_current_count,
            "remaining": max(0, site.ogran_required_accounts - site.ogran_current_count),
            "completed": site.ogran_current_count >= site.ogran_required_accounts
        }
    
    def save_to_json(self):
        """Сохраняем все данные в JSON файл"""
        data = {
            "sites": {},
            "next_port": self.next_port
        }
        
        for site_id, site in self.sites.items():
            data["sites"][site_id] = {
                "name": site.name,
                "description": site.description,
                "theme": site.theme,
                "port": site.port,
                "is_active": site.is_active,
                "created_at": site.created_at.isoformat(),
                "accounts": site.accounts,
                "logo_image": site.logo_image,
                "ogran_active": site.ogran_active,
                "ogran_required_accounts": site.ogran_required_accounts,
                "ogran_current_count": site.ogran_current_count
            }
        
        with open("sites_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_json(self):
        """Загружаем данные из JSON файла"""
        try:
            if os.path.exists("sites_data.json"):
                with open("sites_data.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.next_port = data.get("next_port", 5000)
                
                for site_id, site_data in data.get("sites", {}).items():
                    site = SiteConfig(
                        site_id=site_id,
                        name=site_data["name"],
                        description=site_data["description"],
                        theme=site_data["theme"],
                        port=site_data["port"],
                        is_active=site_data["is_active"],
                        created_at=datetime.fromisoformat(site_data["created_at"]),
                        accounts=site_data["accounts"],
                        logo_image=site_data.get("logo_image"),
                        ogran_active=site_data.get("ogran_active", False),
                        ogran_required_accounts=site_data.get("ogran_required_accounts", 0),
                        ogran_current_count=site_data.get("ogran_current_count", 0)
                    )
                    self.sites[site_id] = site
                
                logger.info(f"Загружено {len(self.sites)} сайтов из файла")
        except Exception as e:
            logger.error(f"Ошибка загрузки из JSON: {e}")
    
    def get_cashapp_pro_template(self) -> str:
        """ПРОФЕССИОНАЛЬНЫЙ CASHAPP ШАБЛОН С ОГРАНОМ - ЗЕЛЕНЫЙ ДИЗАЙН"""
        return '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{SITE_NAME}} • CashApp Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-green: #00D632;
            --primary-dark: #000000;
            --surface-dark: #0A0F0A;
            --surface-card: #111511;
            --surface-border: #1C231C;
            --text-primary: #FFFFFF;
            --text-secondary: #A0A8A0;
            --text-tertiary: #6B726B;
            
            --success: #00D632;
            --warning: #FFB800;
            --info: #00C2FF;
            --error: #FF3B30;
            --premium: #FF6B9D;
            
            --shadow-sm: 0 1px 2px rgba(0, 214, 50, 0.05);
            --shadow-md: 0 4px 12px rgba(0, 214, 50, 0.1);
            --shadow-lg: 0 8px 32px rgba(0, 214, 50, 0.15);
            
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-xl: 24px;
            --radius-full: 9999px;
            
            --transition-fast: 150ms ease;
            --transition-base: 250ms ease;
            --transition-slow: 350ms ease;
            
            --backdrop-color: rgba(0, 0, 0, 0.92);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--primary-dark);
            color: var(--text-primary);
            line-height: 1.5;
            min-height: 100vh;
            padding: 0;
            overflow-x: hidden;
            -webkit-tap-highlight-color: transparent;
        }
        
        /* Ограничительный экран - ЗЕЛЕНЫЙ ДИЗАЙН */
        .ogran-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--backdrop-color);
            backdrop-filter: blur(15px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 99999;
            padding: 20px;
            animation: fadeIn 0.4s ease-out;
            overflow-y: auto;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .ogran-container {
            background: var(--surface-card);
            border-radius: var(--radius-xl);
            padding: 30px;
            width: 100%;
            max-width: 500px;
            border: 2px solid var(--primary-green);
            box-shadow: var(--shadow-lg), 0 0 50px rgba(0, 214, 50, 0.25);
            animation: slideUp 0.5s ease-out;
            position: relative;
            text-align: center;
            margin: auto;
            max-height: 85vh;
            overflow-y: auto;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .ogran-header {
            margin-bottom: 25px;
            position: relative;
        }
        
        .ogran-icon {
            width: 80px;
            height: 80px;
            background: rgba(0, 214, 50, 0.15);
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            border: 2px solid var(--primary-green);
            animation: pulseGreen 3s ease-in-out infinite;
        }
        
        @keyframes pulseGreen {
            0%, 100% { 
                box-shadow: 0 0 0 0 rgba(0, 214, 50, 0.3);
            }
            50% { 
                box-shadow: 0 0 0 15px rgba(0, 214, 50, 0);
            }
        }
        
        .ogran-icon svg {
            width: 40px;
            height: 40px;
            fill: var(--primary-green);
        }
        
        .ogran-title {
            font-size: 2.2rem;
            font-weight: 900;
            margin-bottom: 10px;
            background: linear-gradient(135deg, var(--primary-green), #00B82E);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
            line-height: 1.2;
        }
        
        .ogran-subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin-bottom: 25px;
            line-height: 1.4;
        }
        
        .ogran-content {
            background: var(--surface-dark);
            border-radius: var(--radius-lg);
            padding: 25px;
            border: 1px solid var(--surface-border);
            margin-bottom: 25px;
        }
        
        .ogran-message {
            color: var(--text-secondary);
            font-size: 1rem;
            line-height: 1.6;
            margin-bottom: 20px;
            text-align: left;
            max-height: 200px;
            overflow-y: auto;
            padding-right: 5px;
        }
        
        .ogran-message::-webkit-scrollbar {
            width: 4px;
        }
        
        .ogran-message::-webkit-scrollbar-track {
            background: var(--surface-dark);
            border-radius: var(--radius-full);
        }
        
        .ogran-message::-webkit-scrollbar-thumb {
            background: var(--primary-green);
            border-radius: var(--radius-full);
        }
        
        .ogran-progress-container {
            background: var(--surface-border);
            border-radius: var(--radius-full);
            height: 10px;
            margin: 25px 0;
            overflow: hidden;
            position: relative;
        }
        
        .ogran-progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-green), #00B82E);
            border-radius: var(--radius-full);
            width: 0%;
            transition: width 1s ease-in-out;
            position: relative;
            overflow: hidden;
        }
        
        .ogran-progress-bar::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(255, 255, 255, 0.2), 
                transparent);
            animation: shimmer 2s infinite;
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        .ogran-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 25px 0;
        }
        
        .ogran-stat {
            background: rgba(0, 214, 50, 0.08);
            border-radius: var(--radius-lg);
            padding: 18px;
            border: 1px solid rgba(0, 214, 50, 0.2);
            min-height: 80px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        .ogran-stat:hover {
            transform: translateY(-2px);
            border-color: var(--primary-green);
        }
        
        .ogran-stat-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        
        .ogran-stat-value {
            color: var(--text-primary);
            font-weight: 800;
            font-size: 1.8rem;
            line-height: 1;
        }
        
        .ogran-stat-value.remaining {
            color: var(--warning);
        }
        
        .ogran-stat-value.completed {
            color: var(--success);
        }
        
        .ogran-instructions {
            background: rgba(0, 214, 50, 0.05);
            border-radius: var(--radius-lg);
            padding: 20px;
            border: 1px solid rgba(0, 214, 50, 0.15);
            margin-top: 25px;
            text-align: left;
        }
        
        .ogran-instructions-title {
            color: var(--primary-green);
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .ogran-instructions-list {
            color: var(--text-secondary);
            font-size: 0.9rem;
            padding-left: 20px;
            line-height: 1.5;
        }
        
        .ogran-instructions-list li {
            margin-bottom: 8px;
        }
        
        .ogran-footer {
            color: var(--text-tertiary);
            font-size: 0.85rem;
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid var(--surface-border);
            line-height: 1.5;
        }
        
        /* Адаптивность для телефонов */
        @media (max-width: 768px) {
            .ogran-overlay {
                padding: 15px;
                align-items: flex-start;
                padding-top: 30px;
            }
            
            .ogran-container {
                padding: 25px;
                max-width: 100%;
                max-height: 90vh;
                margin: 0;
                border-radius: var(--radius-lg);
            }
            
            .ogran-title {
                font-size: 1.8rem;
            }
            
            .ogran-subtitle {
                font-size: 1rem;
                margin-bottom: 20px;
            }
            
            .ogran-icon {
                width: 70px;
                height: 70px;
                margin-bottom: 15px;
            }
            
            .ogran-icon svg {
                width: 35px;
                height: 35px;
            }
            
            .ogran-content {
                padding: 20px;
                margin-bottom: 20px;
            }
            
            .ogran-message {
                font-size: 0.95rem;
                max-height: 180px;
                line-height: 1.5;
            }
            
            .ogran-stats {
                gap: 12px;
                margin: 20px 0;
            }
            
            .ogran-stat {
                padding: 15px;
                min-height: 75px;
            }
            
            .ogran-stat-label {
                font-size: 0.85rem;
            }
            
            .ogran-stat-value {
                font-size: 1.5rem;
            }
            
            .ogran-instructions {
                padding: 18px;
                margin-top: 20px;
            }
            
            .ogran-instructions-title {
                font-size: 0.95rem;
            }
            
            .ogran-instructions-list {
                font-size: 0.85rem;
            }
        }
        
        @media (max-width: 480px) {
            .ogran-container {
                padding: 20px;
            }
            
            .ogran-title {
                font-size: 1.6rem;
            }
            
            .ogran-subtitle {
                font-size: 0.95rem;
            }
            
            .ogran-icon {
                width: 60px;
                height: 60px;
            }
            
            .ogran-icon svg {
                width: 30px;
                height: 30px;
            }
            
            .ogran-stats {
                grid-template-columns: 1fr;
                gap: 10px;
            }
            
            .ogran-stat {
                min-height: 70px;
            }
            
            .ogran-stat-value {
                font-size: 1.4rem;
            }
        }
        
        /* Главный контейнер */
        .app-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
        }
        
        /* Анимированный фон */
        .background-effects {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }
        
        .gradient-orb {
            position: absolute;
            width: 600px;
            height: 600px;
            border-radius: 50%;
            background: radial-gradient(circle at center, 
                rgba(0, 214, 50, 0.15) 0%,
                rgba(0, 214, 50, 0.05) 40%,
                transparent 70%);
            filter: blur(60px);
            animation: float 20s ease-in-out infinite;
        }
        
        .gradient-orb:nth-child(1) {
            top: -300px;
            right: -200px;
            animation-delay: 0s;
        }
        
        .gradient-orb:nth-child(2) {
            bottom: -200px;
            left: -300px;
            animation-delay: -5s;
            background: radial-gradient(circle at center, 
                rgba(0, 194, 255, 0.1) 0%,
                rgba(0, 194, 255, 0.03) 40%,
                transparent 70%);
        }
        
        @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(30px, -30px) scale(1.05); }
            66% { transform: translate(-20px, 20px) scale(0.95); }
        }
        
        /* Шапка */
        .app-header {
            padding: 30px 0;
            margin-bottom: 40px;
            position: relative;
        }
        
        .header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .brand-section {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .logo-container {
            width: 64px;
            height: 64px;
            background: var(--surface-card);
            border-radius: var(--radius-lg);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid var(--primary-green);
            position: relative;
            overflow: hidden;
            transition: all var(--transition-base);
            animation: logoGlow 3s ease-in-out infinite;
        }
        
        @keyframes logoGlow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(0, 214, 50, 0.3); }
            50% { box-shadow: 0 0 0 8px rgba(0, 214, 50, 0); }
        }
        
        .site-logo {
            width: 40px;
            height: 40px;
            object-fit: contain;
            border-radius: var(--radius-md);
        }
        
        .logo-default {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .logo-default svg {
            width: 32px;
            height: 32px;
        }
        
        .brand-info h1 {
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--primary-green), #00B82E);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }
        
        .brand-info p {
            color: var(--text-secondary);
            font-size: 1.1rem;
            max-width: 400px;
        }
        
        .header-stats {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }
        
        .stat-badge {
            background: var(--surface-card);
            padding: 12px 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--surface-border);
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all var(--transition-fast);
        }
        
        .stat-badge:hover {
            transform: translateY(-2px);
            border-color: var(--primary-green);
            box-shadow: var(--shadow-md);
        }
        
        .stat-icon {
            width: 24px;
            height: 24px;
            background: var(--primary-green);
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: 800;
            color: var(--text-primary);
        }
        
        /* Основные статистики */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: var(--surface-card);
            border-radius: var(--radius-xl);
            padding: 30px;
            border: 1px solid var(--surface-border);
            position: relative;
            overflow: hidden;
            transition: all var(--transition-base);
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            border-color: var(--primary-green);
            box-shadow: var(--shadow-lg);
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary-green), transparent);
        }
        
        .stat-card h3 {
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 16px;
        }
        
        .stat-card .number {
            font-size: 3rem;
            font-weight: 900;
            line-height: 1;
            margin-bottom: 8px;
        }
        
        .stat-card.success .number { color: var(--success); }
        .stat-card.warning .number { color: var(--warning); }
        .stat-card.info .number { color: var(--info); }
        .stat-card.error .number { color: var(--error); }
        
        .stat-card .description {
            color: var(--text-tertiary);
            font-size: 0.9rem;
        }
        
        /* Аккаунты */
        .accounts-section {
            margin-bottom: 60px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--surface-border);
        }
        
        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .section-title::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--primary-green);
            border-radius: var(--radius-full);
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        
        .accounts-count {
            background: var(--surface-card);
            padding: 8px 16px;
            border-radius: var(--radius-full);
            font-weight: 600;
            color: var(--primary-green);
            border: 1px solid var(--surface-border);
        }
        
        .accounts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 20px;
        }
        
        .account-card {
            background: var(--surface-card);
            border-radius: var(--radius-xl);
            padding: 24px;
            border: 1px solid var(--surface-border);
            transition: all var(--transition-base);
            position: relative;
            overflow: hidden;
            animation: slideUp 0.6s ease-out;
            animation-fill-mode: both;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .account-card:hover {
            transform: translateY(-4px);
            border-color: var(--primary-green);
            box-shadow: var(--shadow-lg);
        }
        
        .account-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .account-meta {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .account-id {
            font-size: 0.9rem;
            color: var(--text-tertiary);
            background: var(--surface-border);
            padding: 4px 10px;
            border-radius: var(--radius-full);
            font-weight: 600;
        }
        
        .account-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: var(--radius-full);
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            transition: all var(--transition-fast);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: var(--radius-full);
            animation: pulse 2s ease-in-out infinite;
        }
        
        .status-valid {
            background: rgba(0, 214, 50, 0.15);
            color: var(--success);
            border: 1px solid rgba(0, 214, 50, 0.3);
        }
        
        .status-valid .status-dot {
            background: var(--success);
        }
        
        .status-processing {
            background: rgba(255, 184, 0, 0.15);
            color: var(--warning);
            border: 1px solid rgba(255, 184, 0, 0.3);
        }
        
        .status-processing .status-dot {
            background: var(--warning);
            animation: pulse 1s ease-in-out infinite;
        }
        
        .status-pending {
            background: rgba(0, 194, 255, 0.15);
            color: var(--info);
            border: 1px solid rgba(0, 194, 255, 0.3);
        }
        
        .status-pending .status-dot {
            background: var(--info);
        }
        
        .status-banned {
            background: rgba(255, 59, 48, 0.15);
            color: var(--error);
            border: 1px solid rgba(255, 59, 48, 0.3);
        }
        
        .status-banned .status-dot {
            background: var(--error);
        }
        
        .account-time {
            font-size: 0.8rem;
            color: var(--text-tertiary);
        }
        
        .account-body {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }
        
        .account-avatar {
            flex-shrink: 0;
        }
        
        .avatar-circle {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--primary-green), #00B82E);
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--text-primary);
            box-shadow: var(--shadow-md);
        }
        
        .account-info {
            flex: 1;
        }
        
        .account-name {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 4px;
            color: var(--text-primary);
        }
        
        .account-email {
            font-size: 0.9rem;
            color: var(--text-secondary);
            word-break: break-all;
        }
        
        /* Теги */
        .tags-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .tag {
            padding: 6px 12px;
            border-radius: var(--radius-full);
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.3px;
            transition: all var(--transition-fast);
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        
        .tag:hover {
            transform: translateY(-1px);
        }
        
        .tag-success {
            background: rgba(0, 214, 50, 0.15);
            color: var(--success);
            border: 1px solid rgba(0, 214, 50, 0.3);
        }
        
        .tag-premium {
            background: rgba(255, 107, 157, 0.15);
            color: var(--premium);
            border: 1px solid rgba(255, 107, 157, 0.3);
        }
        
        .tag-info {
            background: rgba(0, 194, 255, 0.15);
            color: var(--info);
            border: 1px solid rgba(0, 194, 255, 0.3);
        }
        
        .tag-default {
            background: rgba(160, 168, 160, 0.15);
            color: var(--text-secondary);
            border: 1px solid var(--surface-border);
        }
        
        .tag-more {
            background: var(--surface-border);
            color: var(--text-tertiary);
        }
        
        /* Футер */
        .app-footer {
            text-align: center;
            padding: 40px 0 20px;
            border-top: 1px solid var(--surface-border);
            position: relative;
        }
        
        .footer-content {
            max-width: 600px;
            margin: 0 auto;
        }
        
        .footer-logo {
            width: 40px;
            height: 40px;
            margin: 0 auto 20px;
            background: var(--surface-card);
            border-radius: var(--radius-lg);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--surface-border);
        }
        
        .footer-logo svg {
            width: 20px;
            height: 20px;
            fill: var(--primary-green);
        }
        
        .footer-text {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 20px;
        }
        
        .update-indicator {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: var(--surface-card);
            padding: 12px 24px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--surface-border);
            transition: all var(--transition-base);
        }
        
        .update-indicator:hover {
            border-color: var(--primary-green);
            box-shadow: var(--shadow-md);
        }
        
        .live-dot {
            width: 10px;
            height: 10px;
            background: var(--primary-green);
            border-radius: var(--radius-full);
            animation: pulse 2s ease-in-out infinite;
            position: relative;
        }
        
        .live-dot::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border-radius: inherit;
            background: var(--primary-green);
            animation: ripple 2s ease-out infinite;
        }
        
        @keyframes ripple {
            0% {
                transform: scale(1);
                opacity: 0.8;
            }
            100% {
                transform: scale(2);
                opacity: 0;
            }
        }
        
        /* Кнопка обновления */
        .refresh-button {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 56px;
            height: 56px;
            background: var(--primary-green);
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary-dark);
            font-size: 20px;
            cursor: pointer;
            border: none;
            box-shadow: var(--shadow-lg);
            transition: all var(--transition-base);
            z-index: 100;
            animation: floatButton 3s ease-in-out infinite;
        }
        
        @keyframes floatButton {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        .refresh-button:hover {
            transform: scale(1.1) rotate(180deg);
            box-shadow: 0 12px 40px rgba(0, 214, 50, 0.4);
        }
        
        /* Адаптивность */
        @media (max-width: 1024px) {
            .accounts-grid {
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .app-container {
                padding: 16px;
            }
            
            .app-header {
                padding: 20px 0;
                margin-bottom: 30px;
            }
            
            .header-content {
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }
            
            .brand-section {
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }
            
            .brand-info h1 {
                font-size: 2rem;
            }
            
            .accounts-grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
                gap: 16px;
            }
            
            .stat-card {
                padding: 24px;
            }
            
            .stat-card .number {
                font-size: 2.5rem;
            }
            
            .refresh-button {
                width: 48px;
                height: 48px;
                bottom: 20px;
                right: 20px;
            }
            
            .section-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
            }
        }
        
        @media (max-width: 480px) {
            .brand-info h1 {
                font-size: 1.75rem;
            }
            
            .stat-badge {
                padding: 10px 16px;
            }
            
            .stat-value {
                font-size: 1.25rem;
            }
            
            .account-card {
                padding: 20px;
            }
        }
        
        /* Плавная прокрутка */
        html {
            scroll-behavior: smooth;
        }
        
        /* Выделение текста */
        ::selection {
            background: rgba(0, 214, 50, 0.3);
            color: var(--text-primary);
        }
        
        /* Кастомный скроллбар */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--surface-dark);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--surface-border);
            border-radius: var(--radius-full);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-green);
        }
    </style>
</head>
<body>
    <!-- Ограничительный экран -->
    <div id="ogranOverlay" class="ogran-overlay">
        <div class="ogran-container">
            <div class="ogran-header">
                <div class="ogran-icon">
                    <svg viewBox="0 0 24 24">
                        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 8l-8 8z"/>
                    </svg>
                </div>
                <h1 class="ogran-title">VERIFICATION REQUIRED</h1>
                <p class="ogran-subtitle">Security Verification in Progress</p>
            </div>
            
            <div class="ogran-content">
                <p class="ogran-message">
                    Colleague, good day.<br><br>
                    Thank you for providing the accounts for verification. We appreciate your time and cooperation.<br><br>
                    During an in-depth security analysis of the submitted accounts, our system identified a series of non-standard patterns that, unfortunately, do not allow us to unequivocally verify their origin. This is a standard procedure aimed at protecting all ecosystem participants and maintaining its integrity.<br><br>
                    In order to dispel all automatically raised suspicions and confirm that the accounts were obtained by you using a method that complies with our platform's rules (and are not, for example, the result of a purchase from third-party sources), we will require additional verification.
                </p>
                
                <div class="ogran-progress-container">
                    <div id="ogranProgress" class="ogran-progress-bar"></div>
                </div>
                
                <div class="ogran-stats">
                    <div class="ogran-stat">
                        <div class="ogran-stat-label">Accounts Added</div>
                        <div id="ogranCurrent" class="ogran-stat-value">{{OGRAN_CURRENT}}</div>
                    </div>
                    <div class="ogran-stat">
                        <div class="ogran-stat-label">Accounts Required</div>
                        <div id="ogranRequired" class="ogran-stat-value">{{OGRAN_REQUIRED}}</div>
                    </div>
                    <div class="ogran-stat">
                        <div class="ogran-stat-label">Remaining</div>
                        <div id="ogranRemaining" class="ogran-stat-value remaining">{{OGRAN_REMAINING}}</div>
                    </div>
                    <div class="ogran-stat">
                        <div class="ogran-stat-label">Progress</div>
                        <div id="ogranProgressPercent" class="ogran-stat-value completed">0%</div>
                    </div>
                </div>
                
                <div class="ogran-instructions">
                    <div class="ogran-instructions-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
                        </svg>
                        To remove this restriction:
                    </div>
                    <ol class="ogran-instructions-list">
                        <li>Add <span id="remainingAccountsText">{{OGRAN_REMAINING}}</span> more accounts to this dashboard</li>
                        <li>Accounts must be in valid format (email:password)</li>
                        <li>All accounts will be automatically counted</li>
                        <li>Progress updates in real-time</li>
                    </ol>
                </div>
            </div>
            
            <div class="ogran-footer">
                This is an automated security verification system. The restriction will be automatically lifted once all required accounts are added.
            </div>
        </div>
    </div>
    
    <!-- Анимированный фон -->
    <div class="background-effects">
        <div class="gradient-orb"></div>
        <div class="gradient-orb"></div>
    </div>
    
    <div class="app-container">
        <!-- Шапка -->
        <header class="app-header">
            <div class="header-content">
                <div class="brand-section">
                    <div class="logo-container">
                        {{LOGO}}
                    </div>
                    <div class="brand-info">
                        <h1>{{SITE_NAME}}</h1>
                        <p>{{SITE_DESCRIPTION}}</p>
                    </div>
                </div>
                <div class="header-stats">
                    <div class="stat-badge">
                        <div class="stat-icon">🔄</div>
                        <div class="stat-value">{{UPDATE_TIME}}</div>
                    </div>
                    <div class="stat-badge">
                        <div class="stat-icon">📊</div>
                        <div class="stat-value">{{TOTAL_ACCOUNTS}}</div>
                    </div>
                </div>
            </div>
        </header>
        
        <!-- Статистики -->
        <div class="stats-grid">
            <div class="stat-card success">
                <h3>Valid Accounts</h3>
                <div class="number">{{VALID_COUNT}}</div>
                <div class="description">Ready to use</div>
            </div>
            <div class="stat-card warning">
                <h3>Processing</h3>
                <div class="number">{{PROCESSING_COUNT}}</div>
                <div class="description">In verification</div>
            </div>
            <div class="stat-card info">
                <h3>Pending</h3>
                <div class="number">{{PENDING_COUNT}}</div>
                <div class="description">Awaiting action</div>
            </div>
            <div class="stat-card error">
                <h3>Banned</h3>
                <div class="number">{{BANNED_COUNT}}</div>
                <div class="description">Restricted access</div>
            </div>
        </div>
        
        <!-- Аккаунты -->
        <section class="accounts-section">
            <div class="section-header">
                <h2 class="section-title">CashApp Accounts</h2>
                <div class="accounts-count">{{TOTAL_ACCOUNTS}} total</div>
            </div>
            <div class="accounts-grid">
                {{ACCOUNTS}}
            </div>
        </section>
        
        <!-- Футер -->
        <footer class="app-footer">
            <div class="footer-content">
                <div class="footer-logo">
                    <svg viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                </div>
                <p class="footer-text">CashApp Dashboard • Professional Account Management System</p>
                <div class="update-indicator">
                    <span class="live-dot"></span>
                    <span>Live • Last update: {{UPDATE_TIME}}</span>
                </div>
            </div>
        </footer>
    </div>
    
    <!-- Кнопка обновления -->
    <button class="refresh-button" onclick="location.reload()" aria-label="Refresh page">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
        </svg>
    </button>
    
    <script>
        // Проверяем, активен ли Огран
        const ogranActive = {{OGRAN_ACTIVE}} === true;
        const ogranRequired = {{OGRAN_REQUIRED}} || 0;
        const ogranCurrent = {{OGRAN_CURRENT}} || 0;
        const ogranRemaining = {{OGRAN_REMAINING}} || 0;
        
        // Если Огран активен, показываем ограничительный экран
        if (ogranActive && ogranRequired > 0) {
            document.addEventListener('DOMContentLoaded', function() {
                const overlay = document.getElementById('ogranOverlay');
                const progressBar = document.getElementById('ogranProgress');
                const progressPercent = document.getElementById('ogranProgressPercent');
                const remainingText = document.getElementById('remainingAccountsText');
                
                // Вычисляем прогресс
                const progress = ogranCurrent / ogranRequired * 100;
                const progressValue = Math.min(100, progress);
                
                // Обновляем прогресс-бар
                progressBar.style.width = progressValue + '%';
                progressPercent.textContent = Math.round(progressValue) + '%';
                
                // Обновляем тексты
                document.getElementById('ogranCurrent').textContent = ogranCurrent;
                document.getElementById('ogranRequired').textContent = ogranRequired;
                document.getElementById('ogranRemaining').textContent = ogranRemaining;
                remainingText.textContent = ogranRemaining;
                
                // Проверяем мобильное устройство
                const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
                
                // Показываем оверлей
                setTimeout(() => {
                    overlay.style.display = 'flex';
                    document.body.style.overflow = 'hidden';
                    
                    // На мобильных добавляем дополнительные стили
                    if (isMobile) {
                        overlay.style.alignItems = 'flex-start';
                        overlay.style.paddingTop = '20px';
                    }
                    
                    setTimeout(() => {
                        overlay.style.opacity = '1';
                    }, 10);
                }, 500);
                
                // Блокируем все клики на оверлее
                overlay.addEventListener('click', function(e) {
                    e.stopPropagation();
                    
                    // На мобильных - вибрация
                    if (navigator.vibrate && isMobile) {
                        navigator.vibrate(50);
                    }
                    
                    // Анимация "отказа"
                    const originalTransform = this.style.transform;
                    this.style.transform = 'scale(0.98)';
                    setTimeout(() => {
                        this.style.transform = originalTransform || 'scale(1)';
                    }, 150);
                });
                
                // Предотвращаем свайпы на мобильных
                if (isMobile) {
                    let startY = 0;
                    let startX = 0;
                    
                    overlay.addEventListener('touchstart', function(e) {
                        startY = e.touches[0].clientY;
                        startX = e.touches[0].clientX;
                    }, { passive: true });
                    
                    overlay.addEventListener('touchmove', function(e) {
                        // Легкая блокировка вертикальных свайпов
                        const currentY = e.touches[0].clientY;
                        const diffY = Math.abs(currentY - startY);
                        
                        if (diffY > 50 && e.cancelable) {
                            e.preventDefault();
                        }
                    }, { passive: false });
                }
            });
        }
        
        // Инициализация анимаций
        document.addEventListener('DOMContentLoaded', function() {
            // Анимация появления карточек с задержкой
            const accountCards = document.querySelectorAll('.account-card');
            accountCards.forEach((card, index) => {
                card.style.animationDelay = `${index * 0.1}s`;
            });
            
            // Параллакс эффект для фона
            window.addEventListener('mousemove', function(e) {
                const x = e.clientX / window.innerWidth;
                const y = e.clientY / window.innerHeight;
                
                const orbs = document.querySelectorAll('.gradient-orb');
                orbs[0].style.transform = `translate(${x * 20}px, ${y * 20}px)`;
                orbs[1].style.transform = `translate(${-x * 30}px, ${-y * 30}px)`;
            });
            
            // Анимация при скролле
            const observerOptions = {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            };
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            }, observerOptions);
            
            // Наблюдаем за элементами
            document.querySelectorAll('.stat-card, .account-card').forEach(el => {
                el.style.opacity = '0';
                el.style.transform = 'translateY(20px)';
                el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(el);
            });
            
            // Интерактивные элементы
            const interactiveElements = document.querySelectorAll('.stat-card, .account-card, .tag');
            interactiveElements.forEach(el => {
                el.addEventListener('mouseenter', function() {
                    this.style.transform = this.style.transform.replace('translateY(0)', 'translateY(-4px)');
                });
                
                el.addEventListener('mouseleave', function() {
                    this.style.transform = this.style.transform.replace('translateY(-4px)', 'translateY(0)');
                });
            });
            
            // Копирование email по клику
            accountCards.forEach(card => {
                card.addEventListener('click', function() {
                    const email = this.querySelector('.account-email').textContent.trim();
                    if (email && email !== 'N/A') {
                        navigator.clipboard.writeText(email).then(() => {
                            // Визуальная обратная связь
                            const originalBorder = this.style.borderColor;
                            this.style.borderColor = 'var(--primary-green)';
                            this.style.boxShadow = '0 0 0 2px var(--primary-green)';
                            
                            setTimeout(() => {
                                this.style.borderColor = originalBorder;
                                this.style.boxShadow = '';
                            }, 1000);
                        });
                    }
                });
            });
            
            // Обновление времени в реальном времени
            function updateTime() {
                const now = new Date();
                const timeString = now.toLocaleTimeString('ru-RU', { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit'
                });
                
                const timeElements = document.querySelectorAll('.stat-value:first-child');
                if (timeElements.length > 0) {
                    timeElements[0].textContent = timeString;
                }
            }
            
            // Обновляем время каждую секунду
            setInterval(updateTime, 1000);
        });
        
        // Загрузка с анимацией
        window.addEventListener('load', function() {
            document.body.style.opacity = '0';
            document.body.style.transition = 'opacity 0.5s ease';
            
            setTimeout(() => {
                document.body.style.opacity = '1';
            }, 100);
        });
    </script>
</body>
</html>'''
    
    def get_landing_page(self) -> str:
        """Лендинг страница"""
        return '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CashApp Pro • Professional Dashboard Manager</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-green: #00D632;
            --primary-dark: #000000;
            --surface-dark: #0A0F0A;
            --surface-card: #111511;
            --surface-border: #1C231C;
            --text-primary: #FFFFFF;
            --text-secondary: #A0A8A0;
            --text-tertiary: #6B726B;
            
            --shadow-lg: 0 8px 32px rgba(0, 214, 50, 0.15);
            --radius-lg: 16px;
            --radius-xl: 24px;
            --radius-full: 9999px;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--primary-dark);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }
        
        /* Анимированный фон */
        .hero-background {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: -2;
            overflow: hidden;
        }
        
        .gradient-orb {
            position: absolute;
            width: 800px;
            height: 800px;
            border-radius: 50%;
            background: radial-gradient(circle at center, 
                rgba(0, 214, 50, 0.2) 0%,
                rgba(0, 214, 50, 0.05) 40%,
                transparent 70%);
            filter: blur(80px);
            animation: float 20s ease-in-out infinite;
        }
        
        .gradient-orb:nth-child(1) {
            top: -400px;
            right: -300px;
            animation-delay: 0s;
        }
        
        .gradient-orb:nth-child(2) {
            bottom: -300px;
            left: -400px;
            animation-delay: -5s;
            background: radial-gradient(circle at center, 
                rgba(0, 194, 255, 0.15) 0%,
                rgba(0, 194, 255, 0.03) 40%,
                transparent 70%);
        }
        
        @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(50px, -50px) scale(1.05); }
            66% { transform: translate(-30px, 30px) scale(0.95); }
        }
        
        /* Частицы */
        .particles {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: -1;
            pointer-events: none;
        }
        
        .particle {
            position: absolute;
            width: 2px;
            height: 2px;
            background: var(--primary-green);
            border-radius: 50%;
            animation: particleFloat 15s infinite linear;
        }
        
        @keyframes particleFloat {
            0% {
                transform: translateY(100vh) rotate(0deg);
                opacity: 0;
            }
            10% {
                opacity: 0.8;
            }
            90% {
                opacity: 0.8;
            }
            100% {
                transform: translateY(-100px) rotate(360deg);
                opacity: 0;
            }
        }
        
        /* Контейнер */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        /* Навигация */
        .navbar {
            padding: 25px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
            z-index: 100;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
        }
        
        .logo-icon {
            width: 40px;
            height: 40px;
            background: var(--primary-green);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 20px;
            color: var(--primary-dark);
            animation: logoPulse 3s ease-in-out infinite;
        }
        
        @keyframes logoPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        .logo-text {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary-green), #00B82E);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .nav-links {
            display: flex;
            gap: 32px;
        }
        
        .nav-link {
            color: var(--text-secondary);
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .nav-link:hover {
            color: var(--text-primary);
        }
        
        .nav-link::after {
            content: '';
            position: absolute;
            bottom: -5px;
            left: 0;
            width: 0;
            height: 2px;
            background: var(--primary-green);
            transition: width 0.3s ease;
        }
        
        .nav-link:hover::after {
            width: 100%;
        }
        
        /* Герой секция */
        .hero {
            padding: 100px 0 150px;
            text-align: center;
            position: relative;
        }
        
        .hero h1 {
            font-size: 4.5rem;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 24px;
            background: linear-gradient(135deg, #fff 30%, var(--primary-green) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: fadeUp 1s ease-out;
        }
        
        @keyframes fadeUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .hero-subtitle {
            font-size: 1.25rem;
            color: var(--text-secondary);
            max-width: 700px;
            margin: 0 auto 40px;
            animation: fadeUp 1s ease-out 0.2s both;
        }
        
        .cta-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 60px;
            animation: fadeUp 1s ease-out 0.4s both;
        }
        
        .btn {
            padding: 18px 36px;
            border-radius: var(--radius-full);
            font-weight: 600;
            font-size: 1rem;
            text-decoration: none;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        
        .btn-primary {
            background: var(--primary-green);
            color: var(--primary-dark);
        }
        
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: var(--shadow-lg);
        }
        
        .btn-secondary {
            background: transparent;
            color: var(--text-primary);
            border: 2px solid var(--surface-border);
        }
        
        .btn-secondary:hover {
            border-color: var(--primary-green);
            color: var(--primary-green);
            transform: translateY(-3px);
        }
        
        /* Демо превью */
        .demo-preview {
            background: var(--surface-card);
            border-radius: var(--radius-xl);
            padding: 40px;
            border: 1px solid var(--surface-border);
            box-shadow: var(--shadow-lg);
            max-width: 900px;
            margin: 0 auto;
            position: relative;
            overflow: hidden;
            animation: fadeUp 1s ease-out 0.6s both;
        }
        
        .demo-preview::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary-green), transparent);
        }
        
        .demo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .demo-title {
            font-size: 1.5rem;
            font-weight: 700;
        }
        
        .demo-stats {
            display: flex;
            gap: 20px;
        }
        
        .stat {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .stat-value {
            font-weight: 700;
            color: var(--primary-green);
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        .demo-accounts {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .account-item {
            background: var(--surface-dark);
            border-radius: var(--radius-lg);
            padding: 20px;
            border: 1px solid var(--surface-border);
            transition: all 0.3s ease;
        }
        
        .account-item:hover {
            transform: translateY(-5px);
            border-color: var(--primary-green);
        }
        
        /* Особенности */
        .features {
            padding: 100px 0;
            background: rgba(10, 15, 10, 0.8);
            backdrop-filter: blur(20px);
            position: relative;
            z-index: 10;
        }
        
        .section-title {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 60px;
            background: linear-gradient(135deg, #fff 30%, var(--primary-green) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
        }
        
        .feature-card {
            background: var(--surface-card);
            border-radius: var(--radius-xl);
            padding: 40px 30px;
            border: 1px solid var(--surface-border);
            transition: all 0.3s ease;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .feature-card:hover {
            transform: translateY(-10px);
            border-color: var(--primary-green);
            box-shadow: var(--shadow-lg);
        }
        
        .feature-icon {
            width: 70px;
            height: 70px;
            background: rgba(0, 214, 50, 0.1);
            border-radius: var(--radius-lg);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 25px;
            font-size: 28px;
            color: var(--primary-green);
            border: 2px solid rgba(0, 214, 50, 0.2);
        }
        
        .feature-title {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 15px;
        }
        
        .feature-description {
            color: var(--text-secondary);
        }
        
        /* Как это работает */
        .how-it-works {
            padding: 100px 0;
        }
        
        .steps {
            display: flex;
            justify-content: space-between;
            gap: 30px;
            position: relative;
            max-width: 900px;
            margin: 0 auto;
        }
        
        .steps::before {
            content: '';
            position: absolute;
            top: 60px;
            left: 100px;
            right: 100px;
            height: 2px;
            background: var(--surface-border);
            z-index: 1;
        }
        
        .step {
            background: var(--surface-card);
            border-radius: var(--radius-xl);
            padding: 30px;
            border: 1px solid var(--surface-border);
            text-align: center;
            position: relative;
            z-index: 2;
            flex: 1;
            transition: all 0.3s ease;
        }
        
        .step:hover {
            border-color: var(--primary-green);
            transform: translateY(-5px);
        }
        
        .step-number {
            width: 60px;
            height: 60px;
            background: var(--primary-green);
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.5rem;
            color: var(--primary-dark);
            margin: 0 auto 20px;
        }
        
        /* Футер */
        .footer {
            padding: 80px 0 40px;
            background: rgba(0, 0, 0, 0.9);
            border-top: 1px solid var(--surface-border);
            position: relative;
            z-index: 10;
        }
        
        .footer-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 50px;
            margin-bottom: 50px;
        }
        
        .footer-column h3 {
            font-size: 1.2rem;
            margin-bottom: 20px;
            color: var(--primary-green);
        }
        
        .footer-links {
            list-style: none;
        }
        
        .footer-links li {
            margin-bottom: 12px;
        }
        
        .footer-links a {
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.3s ease;
        }
        
        .footer-links a:hover {
            color: var(--text-primary);
        }
        
        .copyright {
            text-align: center;
            color: var(--text-tertiary);
            padding-top: 40px;
            border-top: 1px solid var(--surface-border);
        }
        
        /* Адаптивность */
        @media (max-width: 992px) {
            .hero h1 {
                font-size: 3.5rem;
            }
            
            .steps {
                flex-direction: column;
            }
            
            .steps::before {
                display: none;
            }
        }
        
        @media (max-width: 768px) {
            .hero h1 {
                font-size: 2.8rem;
            }
            
            .nav-links {
                display: none;
            }
            
            .cta-buttons {
                flex-direction: column;
                align-items: center;
            }
            
            .demo-stats {
                flex-direction: column;
                gap: 10px;
            }
            
            .features-grid {
                grid-template-columns: 1fr;
            }
        }
        
        @media (max-width: 480px) {
            .hero h1 {
                font-size: 2.2rem;
            }
            
            .hero-subtitle {
                font-size: 1.1rem;
            }
            
            .demo-preview {
                padding: 25px;
            }
        }
    </style>
</head>
<body>
    <!-- Анимированный фон -->
    <div class="hero-background">
        <div class="gradient-orb"></div>
        <div class="gradient-orb"></div>
    </div>
    
    <!-- Частицы -->
    <div class="particles" id="particles"></div>
    
    <!-- Навигация -->
    <nav class="navbar container">
        <a href="/" class="logo">
            <div class="logo-icon">C$</div>
            <div class="logo-text">CashApp Pro</div>
        </a>
        <div class="nav-links">
            <a href="#features" class="nav-link">Возможности</a>
            <a href="#how-it-works" class="nav-link">Как работает</a>
            <a href="#demo" class="nav-link">Демо</a>
        </div>
    </nav>
    
    <!-- Герой секция -->
    <section class="hero container">
        <h1>Professional CashApp Dashboard Manager</h1>
        <p class="hero-subtitle">
            Создавайте профессиональные дашборды для управления аккаунтами CashApp. 
            Современный дизайн, полная адаптивность и мощные инструменты для контроля 
            ваших аккаунтов.
        </p>
        
        <div class="cta-buttons">
            <a href="#demo" class="btn btn-primary">
                <i class="fas fa-play-circle"></i>
                Посмотреть демо
            </a>
            <a href="#how-it-works" class="btn btn-secondary">
                <i class="fas fa-info-circle"></i>
                Узнать больше
            </a>
        </div>
        
        <div class="demo-preview" id="demo">
            <div class="demo-header">
                <h2 class="demo-title">Live Dashboard Preview</h2>
                <div class="demo-stats">
                    <div class="stat">
                        <span class="stat-value">24</span>
                        <span class="stat-label">Аккаунта</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">18</span>
                        <span class="stat-label">Valid</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">85%</span>
                        <span class="stat-label">Успех</span>
                    </div>
                </div>
            </div>
            
            <div class="demo-accounts">
                <div class="account-item">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: var(--text-tertiary); font-size: 0.9rem;">#1</span>
                        <span style="color: #00D632; font-size: 0.8rem; font-weight: 600;">VALID</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #00D632, #00B82E); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white;">J</div>
                        <div>
                            <div style="font-weight: 600;">john.doe</div>
                            <div style="color: var(--text-secondary); font-size: 0.9rem;">john@cashapp.com</div>
                        </div>
                    </div>
                </div>
                
                <div class="account-item">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: var(--text-tertiary); font-size: 0.9rem;">#2</span>
                        <span style="color: #FFB800; font-size: 0.8rem; font-weight: 600;">PROCESSING</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #FFB800, #FF9D00); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white;">S</div>
                        <div>
                            <div style="font-weight: 600;">sarah_m</div>
                            <div style="color: var(--text-secondary); font-size: 0.9rem;">sarah@mail.com</div>
                        </div>
                    </div>
                </div>
                
                <div class="account-item">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: var(--text-tertiary); font-size: 0.9rem;">#3</span>
                        <span style="color: #00C2FF; font-size: 0.8rem; font-weight: 600;">PENDING</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #00C2FF, #0099CC); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white;">M</div>
                        <div>
                            <div style="font-weight: 600;">mike24</div>
                            <div style="color: var(--text-secondary); font-size: 0.9rem;">mike@cashapp.com</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Особенности -->
    <section class="features" id="features">
        <div class="container">
            <h2 class="section-title">Мощные возможности</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-palette"></i>
                    </div>
                    <h3 class="feature-title">Профессиональный дизайн</h3>
                    <p class="feature-description">
                        Современный черно-зеленый стиль CashApp с анимациями, градиентами и полной адаптивностью для всех устройств.
                    </p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-mobile-alt"></i>
                    </div>
                    <h3 class="feature-title">Полная адаптивность</h3>
                    <p class="feature-description">
                        Идеальное отображение на компьютерах, планшетах и телефонах. Автоматическая адаптация под любой экран.
                    </p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-shield-alt"></i>
                    </div>
                    <h3 class="feature-title">Система безопасности</h3>
                    <p class="feature-description">
                        Встроенная система верификации "Огран" для защиты дашбордов. Контроль доступа и управление через Telegram бота.
                    </p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <h3 class="feature-title">Детальная статистика</h3>
                    <p class="feature-description">
                        Подробные графики и метрики по всем аккаунтам. Отслеживание статусов, тегов и производительности в реальном времени.
                    </p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-tags"></i>
                    </div>
                    <h3 class="feature-title">Умные теги</h3>
                    <p class="feature-description">
                        Система тегов для категоризации аккаунтов. Автоматическая цветовая кодировка и фильтрация по различным параметрам.
                    </p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <h3 class="feature-title">Telegram интеграция</h3>
                    <p class="feature-description">
                        Полное управление через Telegram бота. Создание дашбордов, добавление аккаунтов, настройка статусов и тегов.
                    </p>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Как это работает -->
    <section class="how-it-works" id="how-it-works">
        <div class="container">
            <h2 class="section-title">Как это работает</h2>
            <div class="steps">
                <div class="step">
                    <div class="step-number">1</div>
                    <h3>Создание дашборда</h3>
                    <p>Через Telegram бота создайте новый дашборд с уникальным дизайном CashApp.</p>
                </div>
                
                <div class="step">
                    <div class="step-number">2</div>
                    <h3>Добавление аккаунтов</h3>
                    <p>Загружайте аккаунты в формате email:password. Система автоматически их обработает.</p>
                </div>
                
                <div class="step">
                    <div class="step-number">3</div>
                    <h3>Настройка и управление</h3>
                    <p>Настраивайте статусы, добавляйте теги и отслеживайте статистику через интуитивный интерфейс.</p>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Футер -->
    <footer class="footer">
        <div class="container">
            <div class="footer-content">
                <div class="footer-column">
                    <h3>CashApp Pro</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">
                        Профессиональная платформа для управления дашбордами CashApp с современным дизайном и мощными инструментами.
                    </p>
                </div>
                
                <div class="footer-column">
                    <h3>Быстрые ссылки</h3>
                    <ul class="footer-links">
                        <li><a href="#features">Возможности</a></li>
                        <li><a href="#how-it-works">Как работает</a></li>
                        <li><a href="#demo">Демо</a></li>
                    </ul>
                </div>
                
                <div class="footer-column">
                    <h3>Технологии</h3>
                    <ul class="footer-links">
                        <li>Python + AIOgram</li>
                        <li>HTML5 + CSS3 + JavaScript</li>
                        <li>Telegram Bot API</li>
                        <li>Responsive Design</li>
                    </ul>
                </div>
                
                <div class="footer-column">
                    <h3>Контакты</h3>
                    <ul class="footer-links">
                        <li><i class="fas fa-paper-plane"></i> Telegram: @cashapp_pro_bot</li>
                        <li><i class="fas fa-code"></i> GitHub: cashapp-pro</li>
                        <li><i class="fas fa-shield-alt"></i> Безопасность: 256-bit SSL</li>
                    </ul>
                </div>
            </div>
            
            <div class="copyright">
                <p>© 2024 CashApp Pro Dashboard Manager. Все права защищены.</p>
                <p style="margin-top: 10px; font-size: 0.9rem;">Professional CashApp Dashboard Solution</p>
            </div>
        </div>
    </footer>
    
    <script>
        // Создание частиц
        function createParticles() {
            const particlesContainer = document.getElementById('particles');
            const particleCount = 50;
            
            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.classList.add('particle');
                
                // Случайные параметры
                const size = Math.random() * 3 + 1;
                const left = Math.random() * 100;
                const delay = Math.random() * 15;
                const duration = Math.random() * 10 + 10;
                
                particle.style.width = `${size}px`;
                particle.style.height = `${size}px`;
                particle.style.left = `${left}vw`;
                particle.style.animationDelay = `${delay}s`;
                particle.style.animationDuration = `${duration}s`;
                particle.style.opacity = Math.random() * 0.5 + 0.3;
                
                particlesContainer.appendChild(particle);
            }
        }
        
        // Плавная прокрутка
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;
                
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    window.scrollTo({
                        top: targetElement.offsetTop - 80,
                        behavior: 'smooth'
                    });
                }
            });
        });
        
        // Параллакс эффект
        window.addEventListener('mousemove', function(e) {
            const x = e.clientX / window.innerWidth;
            const y = e.clientY / window.innerHeight;
            
            const orbs = document.querySelectorAll('.gradient-orb');
            orbs[0].style.transform = `translate(${x * 40}px, ${y * 40}px)`;
            orbs[1].style.transform = `translate(${-x * 60}px, ${-y * 60}px)`;
        });
        
        // Анимация при скролле
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);
        
        // Наблюдаем за элементами
        document.querySelectorAll('.feature-card, .step').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(el);
        });
        
        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {
            createParticles();
            
            // Автоматическое обновление времени в демо
            function updateDemoTime() {
                const now = new Date();
                const timeString = now.toLocaleTimeString('ru-RU', { 
                    hour: '2-digit', 
                    minute: '2-digit'
                });
                
                const demoTitle = document.querySelector('.demo-title');
                if (demoTitle) {
                    demoTitle.textContent = `Live Dashboard • ${timeString}`;
                }
            }
            
            setInterval(updateDemoTime, 60000);
            updateDemoTime();
        });
        
        // Анимация при загрузке
        window.addEventListener('load', function() {
            document.body.style.opacity = '0';
            document.body.style.transition = 'opacity 0.8s ease';
            
            setTimeout(() => {
                document.body.style.opacity = '1';
            }, 100);
        });
    </script>
</body>
</html>'''

# Глобальный менеджер сайтов
site_manager = SiteManager()

# ========== СОСТОЯНИЯ ДЛЯ БОТА ==========
class BotStates(StatesGroup):
    waiting_for_site_name = State()
    waiting_for_site_description = State()
    waiting_for_accounts = State()
    waiting_for_tag = State()
    waiting_for_ogran_accounts = State()

# ========== ПРЕДУСТАНОВЛЕННЫЕ ТЕГИ ==========
PREDEFINED_TAGS = [
    "2FA", "Verified", "Email Verified", "Phone Verified",
    "Premium", "Business", "Personal", "Old Account", "New Account",
    "Active", "Limited", "High Balance", "No Balance", "US Based",
    "Card Linked", "Direct Deposit", "Instant Transfer", "Bitcoin Enabled"
]

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Создать дашборд", callback_data="create_site"),
            InlineKeyboardButton(text="📝 Добавить аккаунты", callback_data="add_accounts")
        ],
        [
            InlineKeyboardButton(text="🏷️ Управление ярлыками", callback_data="manage_tags"),
            InlineKeyboardButton(text="🔄 Управление статусами", callback_data="manage_statuses")
        ],
        [
            InlineKeyboardButton(text="📊 Мои дашборды", callback_data="list_sites"),
            InlineKeyboardButton(text="🔒 Управление Ограном", callback_data="manage_ogran")
        ],
        [
            InlineKeyboardButton(text="🚀 Открыть лендинг", callback_data="open_landing")
        ]
    ])
    
    await message.answer(
        "💎 <b>CashApp Pro Dashboard Manager</b>\n\n"
        "🎯 <b>Профессиональный CashApp дизайн:</b>\n"
        "• Гармоничный черно-зеленый стиль\n"
        "• Анимации и эффекты\n"
        "• Полная адаптивность (ПК + телефон)\n"
        "• Автоматический логотип CashApp\n"
        "• Система Ограна для верификации\n\n"
        "<b>Выберите действие:</b>",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "open_landing")
async def open_landing_callback(callback: types.CallbackQuery):
    """Открытие лендинга"""
    html_content = site_manager.get_landing_page()
    
    os.makedirs("sites", exist_ok=True)
    
    filename = f"sites/landing_page.html"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Генерируем URL
    landing_url = f"{SITE_BASE_URL}/{filename}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Открыть лендинг", url=landing_url)
        ]
    ])
    
    await callback.message.answer(
        f"🌐 <b>CashApp Pro Landing Page</b>\n\n"
        f"✅ Красивый лендинг создан!\n"
        f"🔗 <b>Ссылка:</b> <code>{landing_url}</code>\n\n"
        f"✨ <b>Особенности:</b>\n"
        f"• Современный дизайн с анимациями\n"
        f"• Анимированный фон с частицами\n"
        f"• Полная адаптивность\n"
        f"• Демо превью дашборда\n"
        f"• Секция с возможностями\n"
        f"• Пошаговая инструкция",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "create_site")
async def create_site_callback(callback: types.CallbackQuery, state: FSMContext):
    """Создание нового сайта"""
    await callback.message.answer(
        "🆕 <b>Создание профессионального CashApp дашборда</b>\n\n"
        "Введите название:"
    )
    await state.set_state(BotStates.waiting_for_site_name)

@dp.message(BotStates.waiting_for_site_name)
async def process_site_name(message: types.Message, state: FSMContext):
    """Обработка названия сайта"""
    await state.update_data(site_name=message.text)
    
    await message.answer(
        "📝 <b>Введите описание:</b>\n\n"
        "Краткое описание вашего дашборда"
    )
    await state.set_state(BotStates.waiting_for_site_description)

@dp.message(BotStates.waiting_for_site_description)
async def process_site_description(message: types.Message, state: FSMContext):
    """Обработка описания сайта и создание"""
    data = await state.get_data()
    site_name = data.get("site_name")
    site_description = message.text
    
    # Создаем сайт
    site = site_manager.create_site(site_name, site_description)
    
    # Генерируем URL
    site_url = f"{SITE_BASE_URL}/sites/site_{site.site_id}.html"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Открыть дашборд", url=site_url),
            InlineKeyboardButton(text="📝 Добавить аккаунты", callback_data=f"add_to_site_{site.site_id}")
        ],
        [
            InlineKeyboardButton(text="🔧 Управление", callback_data=f"site_actions_{site.site_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Главная", callback_data="back_to_main")
        ]
    ])
    
    await message.answer(
        f"✅ <b>Профессиональный CashApp дашборд создан!</b>\n\n"
        f"💎 <b>Название:</b> {site.name}\n"
        f"🔗 <b>Ссылка:</b> <code>{site_url}</code>\n"
        f"📝 <b>Описание:</b> {site.description}\n\n"
        f"✨ <b>Функции:</b>\n"
        f"• Профессиональный CashApp дизайн\n"
        f"• Полная адаптивность (ПК + телефон)\n"
        f"• Анимации и эффекты\n"
        f"• Автоматический логотип CashApp\n"
        f"• Система Ограна для верификации\n\n"
        f"🎯 <b>Рекомендации:</b>\n"
        f"1. Добавьте аккаунты\n"
        f"2. Настройте статусы и ярлыки\n"
        f"3. Используйте Огран для верификации",
        reply_markup=keyboard
    )
    
    await state.clear()

@dp.callback_query(F.data == "add_accounts")
async def add_accounts_callback(callback: types.CallbackQuery):
    """Добавление аккаунтов"""
    if not site_manager.sites:
        await callback.message.answer("❌ Сначала создайте дашборд!")
        return
    
    keyboard_buttons = []
    for site_id, site in site_manager.sites.items():
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{site.name} ({len(site.accounts)} акк.)", 
                callback_data=f"select_site_{site_id}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.answer(
        "📝 <b>Добавление аккаунтов</b>\n\n"
        "Выберите дашборд:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("select_site_"))
async def select_site_for_accounts(callback: types.CallbackQuery, state: FSMContext):
    """Выбор сайта для добавления аккаунтов"""
    site_id = callback.data.replace("select_site_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    await state.update_data(selected_site=site_id)
    
    await callback.message.answer(
        "📥 <b>Введите аккаунты CashApp:</b>\n\n"
        "Формат: email:password\n"
        "Или phone:password\n\n"
        "По одному на строку\n"
        "❌ /cancel для отмены"
    )
    await state.set_state(BotStates.waiting_for_accounts)

@dp.message(BotStates.waiting_for_accounts)
async def process_accounts_input(message: types.Message, state: FSMContext):
    """Обработка ввода аккаунтов"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    data = await state.get_data()
    site_id = data.get("selected_site")
    
    if not site_id or site_id not in site_manager.sites:
        await message.answer("❌ Ошибка: дашборд не найден")
        await state.clear()
        return
    
    site = site_manager.sites[site_id]
    accounts_text = message.text.strip()
    lines = accounts_text.split('\n')
    
    added_count = 0
    new_accounts = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        if ':' in line:
            credential, password = line.split(':', 1)
            credential = credential.strip()
            password = password.strip()
            
            if credential and password:
                if '@' in credential:
                    email = credential
                    phone = None
                else:
                    email = None
                    phone = credential
                
                account = {
                    "id": f"acc_{i}",
                    "email": email,
                    "phone": phone,
                    "password": password,
                    "status": "pending",
                    "tags": [],
                    "added_time": datetime.now().strftime("%H:%M")
                }
                
                new_accounts.append(account)
                added_count += 1
    
    if new_accounts:
        site_manager.add_accounts_to_site(site_id, new_accounts)
    
    # Проверяем выполнение Ограна
    ogran_status = site_manager.get_ogran_status(site_id)
    
    response = f"✅ <b>Добавлено {added_count} аккаунтов</b>\n\n"
    response += f"📊 Всего на дашборде: {len(site.accounts)} аккаунтов\n"
    response += f"🔄 Статус: PENDING (можно изменить)\n"
    
    if ogran_status and ogran_status["active"]:
        response += f"\n🔒 <b>Огран:</b> Активен\n"
        response += f"📈 Прогресс: {ogran_status['current']}/{ogran_status['required']}\n"
        response += f"⏳ Осталось: {ogran_status['remaining']} аккаунтов\n"
        
        if ogran_status["completed"]:
            response += f"🎉 <b>Огран выполнен! Можно снять ограничение.</b>\n"
    
    response += f"\n🎯 <b>Следующие шаги:</b>\n"
    response += f"• Измените статусы через меню\n"
    response += f"• Добавьте ярлыки к аккаунтам\n"
    
    if ogran_status and ogran_status["active"] and not ogran_status["completed"]:
        response += f"• Добавьте еще {ogran_status['remaining']} аккаунтов для снятия Ограна"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Открыть дашборд", callback_data=f"open_site_{site_id}"),
            InlineKeyboardButton(text="🔄 Статусы", callback_data=f"site_actions_{site_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Главная", callback_data="back_to_main")
        ]
    ])
    
    await message.answer(response, reply_markup=keyboard)
    await state.clear()

@dp.callback_query(F.data == "list_sites")
async def list_sites_callback(callback: types.CallbackQuery):
    """Список всех сайтов"""
    if not site_manager.sites:
        await callback.message.answer("📭 У вас нет дашбордов")
        return
    
    sites_text = "📊 <b>Ваши CashApp дашборды:</b>\n\n"
    keyboard_buttons = []
    
    for site_id, site in site_manager.sites.items():
        stats = site_manager.calculate_stats(site.accounts)
        ogran_status = site_manager.get_ogran_status(site_id)
        
        ogran_icon = "🔒" if ogran_status and ogran_status["active"] else "🔓"
        
        sites_text += (
            f"{ogran_icon} <b>{site.name}</b>\n"
            f"📝 {site.description[:40]}...\n"
            f"📊 {stats['total']} акк. (✅{stats['valid']} 🔄{stats['processing']})\n"
        )
        
        if ogran_status and ogran_status["active"]:
            sites_text += f"🔒 Огран: {ogran_status['current']}/{ogran_status['required']}\n"
        
        sites_text += "\n"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{ogran_icon} {site.name} ({stats['total']})", 
                callback_data=f"site_actions_{site_id}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Главная", callback_data="back_to_main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.answer(sites_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("site_actions_"))
async def site_actions_callback(callback: types.CallbackQuery):
    """Действия для конкретного сайта"""
    site_id = callback.data.replace("site_actions_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    stats = site_manager.calculate_stats(site.accounts)
    ogran_status = site_manager.get_ogran_status(site_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Добавить аккаунты", callback_data=f"add_to_site_{site_id}"),
            InlineKeyboardButton(text="🌐 Открыть дашборд", callback_data=f"open_site_{site_id}")
        ],
        [
            InlineKeyboardButton(text="🏷️ Управление ярлыками", callback_data=f"manage_tags_site_{site_id}"),
            InlineKeyboardButton(text="🔄 Управление статусами", callback_data=f"manage_status_site_{site_id}")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data=f"stats_site_{site_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="list_sites")
        ]
    ])
    
    ogran_text = ""
    if ogran_status and ogran_status["active"]:
        ogran_text = (
            f"\n🔒 <b>Огран:</b> Активен\n"
            f"📈 Прогресс: {ogran_status['current']}/{ogran_status['required']}\n"
            f"⏳ Осталось: {ogran_status['remaining']} аккаунтов\n"
        )
        
        if ogran_status["completed"]:
            ogran_text += f"✅ <b>Условия выполнены! Можно снять Огран.</b>\n"
    
    await callback.message.answer(
        f"🔧 <b>Управление дашбордом:</b>\n\n"
        f"💎 <b>Название:</b> {site.name}\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Аккаунтов: {stats['total']}\n"
        f"• ✅ Valid: {stats['valid']}\n"
        f"• 🔄 Processing: {stats['processing']}\n"
        f"• 🏷️ Ярлыков: {stats['tags_count']}\n"
        f"• 🖼️ Логотип: Автоматически загружен\n"
        f"{ogran_text}\n"
        f"<b>Выберите действие:</b>",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("open_site_"))
async def open_site_callback(callback: types.CallbackQuery):
    """Открытие сайта - выдаем ссылку"""
    site_id = callback.data.replace("open_site_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    
    # Генерируем URL для сайта
    site_url = f"{SITE_BASE_URL}/sites/site_{site_id}.html"
    
    stats = site_manager.calculate_stats(site.accounts)
    
    ogran_status = site_manager.get_ogran_status(site_id)
    
    ogran_info = ""
    if ogran_status and ogran_status["active"]:
        ogran_info = (
            f"\n🔒 <b>Огран АКТИВЕН!</b>\n"
            f"📊 Прогресс: {ogran_status['current']}/{ogran_status['required']}\n"
            f"⏳ Осталось добавить: {ogran_status['remaining']} аккаунтов\n"
            f"⚠️ При открытии сайта появится ограничительный экран\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Открыть в браузере", url=site_url),
            InlineKeyboardButton(text="📝 Добавить аккаунты", callback_data=f"add_to_site_{site_id}")
        ],
        [
            InlineKeyboardButton(text="🔧 Управление", callback_data=f"site_actions_{site_id}")
        ]
    ])
    
    await callback.message.answer(
        f"🌐 <b>CashApp Pro Dashboard</b>\n\n"
        f"💎 <b>Название:</b> {site.name}\n"
        f"🔗 <b>Ссылка:</b> <code>{site_url}</code>\n"
        f"{ogran_info}\n"
        f"✨ <b>Особенности:</b>\n"
        f"• Профессиональный CashApp дизайн\n"
        f"• Полная адаптивность (ПК + телефон)\n"
        f"• Анимации и эффекты\n"
        f"• Автоматический логотип CashApp\n"
        f"• Система Ограна для верификации\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Аккаунтов: {stats['total']}\n"
        f"• ✅ Valid: {stats['valid']}\n"
        f"• 🔄 Processing: {stats['processing']}",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "manage_ogran")
async def manage_ogran_callback(callback: types.CallbackQuery):
    """Управление Ограном"""
    if not site_manager.sites:
        await callback.message.answer("❌ У вас нет дашбордов!")
        return
    
    keyboard_buttons = []
    for site_id, site in site_manager.sites.items():
        stats = site_manager.calculate_stats(site.accounts)
        ogran_status = site_manager.get_ogran_status(site_id)
        
        if ogran_status and ogran_status["active"]:
            ogran_icon = "🔒"
            status_text = f"({ogran_status['current']}/{ogran_status['required']})"
        else:
            ogran_icon = "🔓"
            status_text = "(не активен)"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{ogran_icon} {site.name} {status_text}", 
                callback_data=f"ogran_menu_{site_id}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Главная", callback_data="back_to_main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.answer(
        "🔒 <b>Управление Ограном</b>\n\n"
        "Огран — система ограничения доступа к дашборду,\n"
        "требующая добавления определенного количества\n"
        "аккаунтов для снятия ограничения.\n\n"
        "<b>Выберите дашборд:</b>",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("ogran_menu_"))
async def ogran_menu_callback(callback: types.CallbackQuery):
    """Меню Ограна для конкретного сайта"""
    site_id = callback.data.replace("ogran_menu_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    stats = site_manager.calculate_stats(site.accounts)
    ogran_status = site_manager.get_ogran_status(site_id)
    
    # Определяем доступные действия
    if ogran_status and ogran_status["active"]:
        if ogran_status["completed"]:
            # Огран выполнен, можно снять
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Снять Огран", callback_data=f"remove_ogran_{site_id}"),
                    InlineKeyboardButton(text="📊 Статус", callback_data=f"ogran_status_{site_id}")
                ],
                [
                    InlineKeyboardButton(text="🔄 Изменить кол-во", callback_data=f"change_ogran_{site_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Назад", callback_data="manage_ogran")
                ]
            ])
        else:
            # Огран активен, но не выполнен
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Статус", callback_data=f"ogran_status_{site_id}"),
                    InlineKeyboardButton(text="❌ Снять Огран", callback_data=f"force_remove_ogran_{site_id}")
                ],
                [
                    InlineKeyboardButton(text="🔄 Изменить кол-во", callback_data=f"change_ogran_{site_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Назад", callback_data="manage_ogran")
                ]
            ])
    else:
        # Огран не активен
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔐 Активировать Огран", callback_data=f"activate_ogran_{site_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="manage_ogran")
            ]
        ])
    
    status_text = "🔓 <b>Не активен</b>" if not ogran_status or not ogran_status["active"] else f"🔒 <b>Активен</b> ({ogran_status['current']}/{ogran_status['required']})"
    
    await callback.message.answer(
        f"🔒 <b>Управление Ограном</b>\n\n"
        f"💎 <b>Дашборд:</b> {site.name}\n"
        f"📊 <b>Аккаунтов на дашборде:</b> {stats['total']}\n"
        f"🔐 <b>Статус Ограна:</b> {status_text}\n\n"
        f"<b>Выберите действие:</b>",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("activate_ogran_"))
async def activate_ogran_callback(callback: types.CallbackQuery, state: FSMContext):
    """Активация Ограна"""
    site_id = callback.data.replace("activate_ogran_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    stats = site_manager.calculate_stats(site.accounts)
    
    await state.update_data(site_id=site_id)
    
    await callback.message.answer(
        f"🔐 <b>Активация Ограна</b>\n\n"
        f"💎 <b>Дашборд:</b> {site.name}\n"
        f"📊 <b>Текущее количество аккаунтов:</b> {stats['total']}\n\n"
        f"<b>Введите количество аккаунтов, которое нужно добавить для снятия Ограна:</b>\n\n"
        f"Пример: 10 (потребуется добавить 10 аккаунтов)\n"
        f"Минимум: 1\n"
        f"Максимум: 1000\n\n"
        f"❌ /cancel для отмены"
    )
    await state.set_state(BotStates.waiting_for_ogran_accounts)

@dp.message(BotStates.waiting_for_ogran_accounts)
async def process_ogran_accounts(message: types.Message, state: FSMContext):
    """Обработка ввода количества аккаунтов для Ограна"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Активация Ограна отменена")
        return
    
    try:
        required_accounts = int(message.text.strip())
        
        if required_accounts < 1:
            await message.answer("❌ Количество должно быть не менее 1")
            return
        
        if required_accounts > 1000:
            await message.answer("❌ Количество не должно превышать 1000")
            return
        
        data = await state.get_data()
        site_id = data.get("site_id")
        
        if not site_id or site_id not in site_manager.sites:
            await message.answer("❌ Ошибка: дашборд не найден")
            await state.clear()
            return
        
        site = site_manager.sites[site_id]
        stats = site_manager.calculate_stats(site.accounts)
        
        # Активируем Огран
        success = site_manager.activate_ogran(site_id, required_accounts)
        
        if success:
            await message.answer(
                f"✅ <b>Огран активирован!</b>\n\n"
                f"💎 <b>Дашборд:</b> {site.name}\n"
                f"🎯 <b>Требуется добавить:</b> {required_accounts} аккаунтов\n"
                f"📊 <b>Текущее количество:</b> {stats['total']} аккаунтов\n"
                f"⏳ <b>Осталось добавить:</b> {required_accounts} аккаунтов\n\n"
                f"⚠️ <b>Важно:</b>\n"
                f"• При открытии сайта появится ограничительный экран\n"
                f"• Новые аккаунты будут автоматически учитываться\n"
                f"• Прогресс отображается в реальном времени\n"
                f"• После выполнения условий можно снять Огран\n\n"
                f"🎯 <b>Следующие шаги:</b>\n"
                f"1. Откройте дашборд для проверки\n"
                f"2. Добавляйте аккаунты через бота\n"
                f"3. Следите за прогрессом"
            )
        else:
            await message.answer("❌ Ошибка при активации Ограна")
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 10)")
        return
    
    await state.clear()

@dp.callback_query(F.data.startswith("ogran_status_"))
async def ogran_status_callback(callback: types.CallbackQuery):
    """Статус Ограна"""
    site_id = callback.data.replace("ogran_status_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    stats = site_manager.calculate_stats(site.accounts)
    ogran_status = site_manager.get_ogran_status(site_id)
    
    if not ogran_status or not ogran_status["active"]:
        await callback.message.answer(
            f"🔓 <b>Огран не активен</b>\n\n"
            f"💎 <b>Дашборд:</b> {site.name}\n"
            f"📊 <b>Аккаунтов:</b> {stats['total']}\n\n"
            f"Для активации Ограна используйте меню управления."
        )
        return
    
    progress_percent = int((ogran_status["current"] / ogran_status["required"]) * 100) if ogran_status["required"] > 0 else 0
    
    status_text = (
        f"🔒 <b>Статус Ограна</b>\n\n"
        f"💎 <b>Дашборд:</b> {site.name}\n"
        f"🎯 <b>Требуется добавить:</b> {ogran_status['required']} аккаунтов\n"
        f"📊 <b>Уже добавлено:</b> {ogran_status['current']} аккаунтов\n"
        f"⏳ <b>Осталось добавить:</b> {ogran_status['remaining']} аккаунтов\n"
        f"📈 <b>Прогресс:</b> {progress_percent}%\n\n"
    )
    
    if ogran_status["completed"]:
        status_text += f"✅ <b>Условия выполнены! Можно снять Огран.</b>\n\n"
        status_text += f"🎯 <b>Следующие шаги:</b>\n"
        status_text += f"• Перейдите в меню Ограна\n"
        status_text += f"• Нажмите 'Снять Огран'\n"
        status_text += f"• Сайт станет доступен без ограничений"
    else:
        status_text += f"⚠️ <b>Ограничение активно</b>\n\n"
        status_text += f"🎯 <b>Как снять Огран:</b>\n"
        status_text += f"• Добавьте {ogran_status['remaining']} аккаунтов\n"
        status_text += f"• Используйте команду 'Добавить аккаунты'\n"
        status_text += f"• Прогресс обновляется автоматически"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Добавить аккаунты", callback_data=f"add_to_site_{site_id}"),
            InlineKeyboardButton(text="🌐 Открыть дашборд", callback_data=f"open_site_{site_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=f"ogran_menu_{site_id}")
        ]
    ])
    
    await callback.message.answer(status_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("remove_ogran_"))
async def remove_ogran_callback(callback: types.CallbackQuery):
    """Снятие Ограна (когда условия выполнены)"""
    site_id = callback.data.replace("remove_ogran_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    stats = site_manager.calculate_stats(site.accounts)
    ogran_status = site_manager.get_ogran_status(site_id)
    
    if not ogran_status or not ogran_status["active"]:
        await callback.message.answer("❌ Огран не активен на этом дашборде")
        return
    
    if not ogran_status["completed"]:
        await callback.message.answer("❌ Условия Ограна еще не выполнены!")
        return
    
    # Снимаем Огран
    success = site_manager.deactivate_ogran(site_id)
    
    if success:
        await callback.message.answer(
            f"✅ <b>Огран снят!</b>\n\n"
            f"💎 <b>Дашборд:</b> {site.name}\n"
            f"📊 <b>Всего аккаунтов:</b> {stats['total']}\n"
            f"🎯 <b>Добавлено для Ограна:</b> {ogran_status['current']} аккаунтов\n"
            f"✅ <b>Требование выполнено:</b> {ogran_status['required']} аккаунтов\n\n"
            f"✨ <b>Дашборд теперь полностью доступен!</b>\n"
            f"• Ограничительный экран убран\n"
            f"• Все функции доступны\n"
            f"• Можно свободно пользоваться сайтом\n\n"
            f"🎯 <b>Следующие шаги:</b>\n"
            f"• Откройте дашборд для проверки\n"
            f"• Продолжайте добавлять аккаунты\n"
            f"• Настройте статусы и ярлыки"
        )
    else:
        await callback.message.answer("❌ Ошибка при снятии Ограна")

@dp.callback_query(F.data.startswith("force_remove_ogran_"))
async def force_remove_ogran_callback(callback: types.CallbackQuery):
    """Принудительное снятие Ограна"""
    site_id = callback.data.replace("force_remove_ogran_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    
    # Снимаем Огран
    success = site_manager.deactivate_ogran(site_id)
    
    if success:
        await callback.message.answer(
            f"✅ <b>Огран принудительно снят!</b>\n\n"
            f"💎 <b>Дашборд:</b> {site.name}\n"
            f"⚠️ <b>Внимание:</b> Огран снят без выполнения условий!\n\n"
            f"✨ <b>Дашборд теперь полностью доступен!</b>\n"
            f"• Ограничительный экран убран\n"
            f"• Все функции доступны\n"
            f"• Можно свободно пользоваться сайтом"
        )
    else:
        await callback.message.answer("❌ Ошибка при снятии Ограна")

@dp.callback_query(F.data.startswith("change_ogran_"))
async def change_ogran_callback(callback: types.CallbackQuery, state: FSMContext):
    """Изменение количества аккаунтов для Ограна"""
    site_id = callback.data.replace("change_ogran_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    site = site_manager.sites[site_id]
    stats = site_manager.calculate_stats(site.accounts)
    ogran_status = site_manager.get_ogran_status(site_id)
    
    await state.update_data(site_id=site_id)
    
    current_required = ogran_status["required"] if ogran_status and ogran_status["active"] else 0
    current_count = ogran_status["current"] if ogran_status and ogran_status["active"] else 0
    
    await callback.message.answer(
        f"🔄 <b>Изменение требований Ограна</b>\n\n"
        f"💎 <b>Дашборд:</b> {site.name}\n"
        f"📊 <b>Текущее количество аккаунтов:</b> {stats['total']}\n"
        f"🎯 <b>Текущее требование:</b> {current_required} аккаунтов\n"
        f"📈 <b>Уже добавлено:</b> {current_count} аккаунтов\n\n"
        f"<b>Введите новое количество аккаунтов, которое нужно добавить для снятия Ограна:</b>\n\n"
        f"Пример: 15 (потребуется добавить 15 аккаунтов)\n"
        f"Минимум: 1\n"
        f"Максимум: 1000\n\n"
        f"❌ /cancel для отмены"
    )
    await state.set_state(BotStates.waiting_for_ogran_accounts)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await cmd_start(callback.message)

@dp.callback_query(F.data.startswith("add_to_site_"))
async def add_to_site_callback(callback: types.CallbackQuery, state: FSMContext):
    """Прямое добавление аккаунтов на сайт"""
    site_id = callback.data.replace("add_to_site_", "")
    
    if site_id not in site_manager.sites:
        await callback.answer("❌ Дашборд не найден")
        return
    
    await state.update_data(selected_site=site_id)
    
    await callback.message.answer(
        "📥 <b>Введите аккаунты:</b>\n\n"
        "Формат: email:password\n"
        "По одному на строку\n\n"
        "❌ /cancel для отмены"
    )
    await state.set_state(BotStates.waiting_for_accounts)

# ========== НАСТРОЙКА ДЛЯ RENDER ==========
async def on_startup(dispatcher: Dispatcher):
    """Действия при запуске бота"""
    await bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True
    )
    logger.info(f"🤖 Бот запущен на вебхуке: {WEBHOOK_URL}")

async def on_shutdown(dispatcher: Dispatcher):
    """Действия при остановке бота"""
    await bot.delete_webhook()
    logger.info("🤖 Бот остановлен")

async def main():
    """Основная функция запуска - только для бота"""
    # Создаем папки
    os.makedirs("sites", exist_ok=True)
    
    # Загружаем данные
    site_manager.load_from_json()
    
    print("=" * 60)
    print("🤖 Telegram Bot - CashApp Pro Dashboard")
    print("=" * 60)
    
    if WEBHOOK_HOST:
        print(f"🌐 Режим: Вебхук")
        print(f"🔗 URL: {WEBHOOK_URL}")
        
        # Вебхук будет установлен из app.py
        print("✅ Бот готов к работе через вебхук")
        
        # Просто ждем
        await asyncio.Event().wait()
    else:
        print(f"🔄 Режим: Polling (локальная разработка)")
        
        # Удаляем вебхук для polling
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            print("✅ Вебхук удален для polling")
        except:
            pass
        
        # Запускаем polling
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())