import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, InputMediaPhoto, \
    KeyboardButton
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

import settings

ORDERS_CHAT_ID = -1001798504591
countries = {'RU': '🇷🇺 Россия', 'FI': '🇫🇮 Финляндия', 'DE': '🇩🇪 Германия', 'US': '🇺🇸 США', 'LV': '🇱🇻 Латвия'}
products = {
    'RU': {
        'Яблоко': ['Apple.jpg'],
        'Груша': ['Pear.jpg']
    },
    'DE': {
        'Витамин D3': ['D3.jpg', 'D3@rev.jpg']
    }}

user_cart = {}

updater = Updater(token=settings.TOKEN)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

button_column = [[KeyboardButton(text='/menu'), KeyboardButton(text='/cart')]]
main_kb = ReplyKeyboardMarkup([button for button in button_column], resize_keyboard=True)


def main_keyboard(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("User %s 'start'", user.first_name)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Добро пожаловать {user.first_name}',
                             reply_markup=main_kb)


start_handler = CommandHandler('start', main_keyboard)
dispatcher.add_handler(start_handler)


def catalog(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("User %s open catalog", user.first_name)
    global catalog_message_id
    buttons_in_row = 3
    buttons = [[]]
    i = 0
    for num, country in enumerate(countries.items()):
        button = (InlineKeyboardButton(text=country[1], callback_data=f'country_{country[0]}'))
        if (num + 1) % buttons_in_row == 0:
            i += 1
            buttons.append([])
        buttons[i].append(button)
    keyboard = InlineKeyboardMarkup([button for button in buttons])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Каталог',
                             reply_markup=keyboard)


menu_handler = CommandHandler('menu', catalog)
dispatcher.add_handler(menu_handler)


def products_catalog(update: Update, context: CallbackContext):
    global products

    chosen_country = update.callback_query.data.split('_')[1]
    if chosen_country in products.keys():
        for product, photo_names in products[chosen_country].items():
            buttons = ([InlineKeyboardButton(text='Добавить', callback_data=f'add_{product}'),
                        InlineKeyboardButton(text='Убрать', callback_data=f'remove_{product}')],)

            if len(photo_names) == 2:
                compounds_url = f'products/{chosen_country}/{photo_names[1]}'
                buttons[0].append(InlineKeyboardButton(text='Состав', callback_data=f'roll_{compounds_url}'))
            keyboard = InlineKeyboardMarkup([button for button in buttons])
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'{product} \n Цена: "в разработке"')
            context.bot.send_photo(chat_id=update.effective_chat.id,
                                   photo=open(f'products/{chosen_country}/{photo_names[0]}', 'rb'),
                                   disable_notification=True,
                                   reply_markup=keyboard)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Товаров из {countries[chosen_country]} нет')


catalog_handler = CallbackQueryHandler(products_catalog, pattern="^" + str('country_'))
dispatcher.add_handler(catalog_handler)


def roll_photo(update: Update, context: CallbackContext):
    call = update.callback_query

    photo_url = call.data.split('_')[1]
    turn_photo = open(photo_url, 'rb')

    main_inline_kb = call.message.reply_markup.inline_keyboard

    if '@rev' in photo_url:
        main_photo = photo_url.replace('@rev', '')
    else:
        main_photo = photo_url.replace('.', '@rev.')

    buttons = ([[InlineKeyboardButton(text='Добавить', callback_data=main_inline_kb[0][0]['callback_data']),
                 InlineKeyboardButton(text='Убрать', callback_data=main_inline_kb[0][1]['callback_data']),
                 InlineKeyboardButton(text='Повернуть', callback_data=f'roll_{main_photo}')]])
    keyboard = InlineKeyboardMarkup([button for button in buttons])
    try:
        context.bot.edit_message_media(
            media=InputMediaPhoto(media=turn_photo),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard)
    except:
        context.bot.send_message(call.message.chat.id, "Хм... состава не оказалось")


roll_photo_handler = CallbackQueryHandler(roll_photo, pattern="^" + str('roll_'))
dispatcher.add_handler(roll_photo_handler)


def add(update: Update, context: CallbackContext):
    global user_cart
    call = update.callback_query
    product = call.data.split('_')[1]
    if product in user_cart:
        user_cart[product] += 1
    else:
        user_cart[product] = 1
    context.bot.answer_callback_query(callback_query_id=call.id, text=f'В корзине {product} - {user_cart[product]} шт.')


catalog_handler = CallbackQueryHandler(add, pattern="^" + str('add_'))
dispatcher.add_handler(catalog_handler)


def remove(update: Update, context: CallbackContext):
    global user_cart
    call = update.callback_query
    product = call.data.split('_')[1]
    if product in user_cart:
        user_cart[product] -= 1
        context.bot.answer_callback_query(callback_query_id=call.id,
                                          text=f'В корзине {product} - {user_cart[product]} шт.')
    else:
        context.bot.answer_callback_query(callback_query_id=call.id, text=f'В корзине нет {product}')


catalog_handler = CallbackQueryHandler(remove, pattern="^" + str('remove_'))
dispatcher.add_handler(catalog_handler)


def cart(update: Update, context: CallbackContext):
    global user_cart

    if update.callback_query:
        user = update.callback_query.message.chat.username
        chat_id = update.callback_query.message.chat_id
        message_id = update.callback_query.message.message_id
    else:
        chat_id = update.effective_chat.id
        user = update.message.from_user.username
    cart_message = f'Корзина {user}: \n'
    buttons = []
    if len(user_cart) > 0:
        buttons = ([InlineKeyboardButton(text='Заказать', callback_data='order'),
                    InlineKeyboardButton(text='Отчистить', callback_data='delete-cart')],)

    keyboard = InlineKeyboardMarkup([button for button in buttons])

    for product in user_cart:
        cart_message += f'{product} - {user_cart[product]} шт. \n'

    if update.callback_query:
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=cart_message,
                                      reply_markup=keyboard)
    else:
        context.bot.send_message(chat_id=chat_id, text=cart_message, reply_markup=keyboard)


cart_handler = CommandHandler('cart', cart)
dispatcher.add_handler(cart_handler)

cancel_cart_handler = CallbackQueryHandler(cart, pattern=str('cancel-delete-cart'))
dispatcher.add_handler(cancel_cart_handler)


def order(update: Update, context: CallbackContext):
    global user_cart
    call = update.callback_query.message
    context.bot.forward_message(chat_id=ORDERS_CHAT_ID,
                                from_chat_id=call.chat_id,
                                message_id=call.message_id)
    # context.bot.delete_message(chat_id=call.chat.id,
    #                            message_id=call.message_id)


order_cart_handler = CallbackQueryHandler(order, pattern=str('order'))
dispatcher.add_handler(order_cart_handler)


def delete_cart(update: Update, context: CallbackContext):
    call = update.callback_query
    global user_cart
    buttons = ([InlineKeyboardButton(text='Вернуться', callback_data='cancel-delete-cart'),
                InlineKeyboardButton(text='Удалить', callback_data='accept-delete-cart')],)

    keyboard = InlineKeyboardMarkup([button for button in buttons])

    context.bot.edit_message_text(chat_id=call.message.chat.id,
                                  message_id=call.message.message_id,
                                  text='Вы уверены что хотите удалить корзину',
                                  reply_markup=keyboard)


delete_cart_handler = CallbackQueryHandler(delete_cart, pattern=str('delete-cart'))
dispatcher.add_handler(delete_cart_handler)


def accept_delete_cart(update: Update, context: CallbackContext):
    global user_cart
    call = update.callback_query
    user_cart = {}
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    context.bot.answer_callback_query(callback_query_id=call.id, text=f'Корзина отчищена')


accept_cart_handler = CallbackQueryHandler(accept_delete_cart, pattern=str('accept-delete-cart'))
dispatcher.add_handler(accept_cart_handler)


def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

if __name__ == '__main__':
    updater.start_polling()
