import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_telegram_notification(chat_id, text, parse_mode='HTML'):
    """Отправляет сообщение в Telegram"""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token or not chat_id:
        logger.warning(f"Telegram: нет токена или chat_id")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        response = requests.post(url, data={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }, timeout=10)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Telegram: сообщение отправлено, ok={result.get('ok')}")
        return result.get('ok', False)
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram error: {e}")
        return False


def send_order_notification_to_client(agreement, price_info, client, final_box, applied_promo):
    """Отправляет уведомление о заказе клиенту в Telegram"""
    
    if not client.telegram_chat_id or not client.telegram_linked:
        logger.info(f"Клиент {client.id} не привязал Telegram")
        return False
    
    # Формируем красивое сообщение
    message = f"""✅ <b>Заказ №{agreement.id} оформлен!</b>

👤 <b>Клиент:</b> {client.full_name}
📞 {client.phone}

📦 <b>Бокс:</b> №{final_box.number if final_box else 'Будет назначен'} 
   Размер: {final_box.box_type.length}×{final_box.box_type.width}×{final_box.box_type.height}м
   Объём: {final_box.box_type.volume if final_box else '-'} м³

🏭 <b>Склад:</b> {agreement.warehouse}

📅 <b>Срок аренды:</b> 
   Начало: {agreement.start_date.strftime('%d.%m.%Y')}
   Окончание: {agreement.end_date.strftime('%d.%m.%Y')}
   Длительность: {price_info['duration']} мес.

💰 <b>Стоимость:</b>
   В месяц: {price_info['monthly_price']} ₽
   Итого: {price_info['total_price']} ₽
   {f"Скидка за срок: {price_info['discount_percent']}%" if price_info['discount_percent'] > 0 else ""}
   {f"🎁 Промокод: {applied_promo.code} (-{applied_promo.discount_percent}%)" if applied_promo else ""}

{"🚚 <b>Доставка:</b> Бесплатная до склада" if agreement.free_delivery else ""}

🔗 <a href="https://antoxaboss.pythonanywhere.com/cabinet/">Личный кабинет</a>"""

    return send_telegram_notification(client.telegram_chat_id, message)