import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, InputMediaPhoto, \
    KeyboardButton
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from market_bot.db_connection import connect_db, load_last_order, save_last_order, get_category, get_products, \
    save_order, get_user_orders, edit_to_cart, show_cart, db_delete_cart, get_product_id
from settings import TOKEN, ORDERS_CHAT_ID

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

button_column = [[KeyboardButton(text='Меню'), KeyboardButton(text='Корзина')], [KeyboardButton(text='Мои заказы')]]
main_kb = ReplyKeyboardMarkup([button for button in button_column], resize_keyboard=True)


def main_keyboard(update: Update, context: CallbackContext):
    '''Основаня клавиатура снизу'''
    user = update.message.from_user
    logger.info("User %s 'start'", user.first_name)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Добро пожаловать {user.first_name}',
                             reply_markup=main_kb)


start_handler = CommandHandler('start', main_keyboard)
dispatcher.add_handler(start_handler)


def catalog(update: Update, context: CallbackContext):
    '''Вызов каталога по группам'''
    user = update.message.from_user
    logger.info("User %s open catalog", user.first_name)
    buttons_in_row = 3
    buttons = [[]]
    row = 0
    for category in get_category():
        button = (InlineKeyboardButton(text=category[2], callback_data=f'category_{category[1]}'))
        if category[0] % buttons_in_row == 0:
            buttons.append([])
            row += 1
        buttons[row].append(button)
    keyboard = InlineKeyboardMarkup([button for button in buttons])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Каталог',
                             reply_markup=keyboard)


menu_handler = MessageHandler(Filters.text('Меню'), catalog)
dispatcher.add_handler(menu_handler)


def products_catalog(update: Update, context: CallbackContext):
    '''Вызов каталога товаров'''
    chosen_category = update.callback_query.data.split('_')[1]
    page = 0
    pagination = False

    if '#' in chosen_category:
        chosen_category, page = chosen_category.split('#')
        page = int(page)
    _, command, category_name = get_category(chosen_category)
    products, pages = get_products(chosen_category, page)
    if pages:
        pagination = True
    if products:
        for product in products:
            product_id, category, product_name, product_img, price, rests, barcode = product
            buttons = ([InlineKeyboardButton(text='Добавить', callback_data=f'add_{product_id}'),
                        InlineKeyboardButton(text='Убрать', callback_data=f'remove_{product_id}')],)
            imgs = [product_img]
            try:
                img_reversed = product_img.replace('.', '@rev.')
                open(f'products/{img_reversed}')
                imgs.append(f'{img_reversed}')
            except FileNotFoundError:
                pass

            if len(imgs) > 1:
                compounds_url = f'products/{imgs[1]}'
                buttons[0].append(InlineKeyboardButton(text='Состав', callback_data=f'roll_{compounds_url}'))
            keyboard = InlineKeyboardMarkup([button for button in buttons])
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'{product_name} '
                                                                            f'\n Цена: {price}')
            context.bot.send_photo(chat_id=update.effective_chat.id,
                                   photo=open(f'products/{imgs[0]}', 'rb'),
                                   disable_notification=True,
                                   reply_markup=keyboard)
        if pagination:
            keyboard_next = InlineKeyboardMarkup([[InlineKeyboardButton(text='Еще товары',
                                                                        callback_data=f'category_{chosen_category}#{page + 1}')]])
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f'Страница {page} из {pages}',
                                     disable_notification=True,
                                     reply_markup=keyboard_next)

    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Товаров из {category_name} нет')


catalog_handler = CallbackQueryHandler(products_catalog, pattern="^" + str('category_'))
dispatcher.add_handler(catalog_handler)


def roll_photo(update: Update, context: CallbackContext):
    '''Показать фото с составом и обратно'''
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


def edit(update: Update, context: CallbackContext):
    '''Добавить/Удаить товар в корзине'''

    call = update.callback_query
    user = call.from_user.username
    command, product_id = call.data.split('_')

    product_amount, product = edit_to_cart(command, user, product_id)
    context.bot.answer_callback_query(callback_query_id=call.id, text=f'В корзине {product} - {product_amount} шт.')


catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('add_'))
dispatcher.add_handler(catalog_handler)

catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('remove_'))
dispatcher.add_handler(catalog_handler)


def cart(update: Update, context: CallbackContext):
    '''Показать корзину покупателя/ Отмена удаления корзины'''
    if update.callback_query:
        user = update.callback_query.message.chat.username
    else:
        user = update.message.from_user.username
    cart_info = show_cart(user)
    cart_price = 0
    cart_message = f'Корзина {user}: \n'
    if len(cart_info) > 0:
        for num, product in enumerate(cart_info):
            product_name, amount, price = product
            cart_price += price * amount
            cart_message += f'{num + 1}. {product_name} - {amount} шт. по {price} р.\n'
        else:
            cart_message += f'Итого: {cart_price} р.'

        buttons = ([InlineKeyboardButton(text='Заказать', callback_data=f'order_{cart_price}'),
                    InlineKeyboardButton(text='Очистить', callback_data='delete-cart')],
                   [InlineKeyboardButton(text='Закрыть', callback_data='remove-message'),
                    InlineKeyboardButton(text='Редактировать', callback_data='correct-cart')])
        keyboard = InlineKeyboardMarkup([button for button in buttons])

        if update.callback_query:
            chat_id = update.callback_query.message.chat_id
            message_id = update.callback_query.message.message_id
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=cart_message,
                                          reply_markup=keyboard)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=cart_message, reply_markup=keyboard)
    else:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f'Корзина пустая',
                                 reply_markup=keyboard)


cart_handler = MessageHandler(Filters.text('Корзина'), cart)
dispatcher.add_handler(cart_handler)

cancel_cart_handler = CallbackQueryHandler(cart, pattern=str('cancel-delete-cart'))
dispatcher.add_handler(cancel_cart_handler)


def edit_cart(update: Update, context: CallbackContext):
    '''Редактирование товаров в корзине'''
    call = update.callback_query
    user = call.message.chat.username
    chat_id = call.message.chat_id
    message_id = call.message.message_id
    command, product_id = call.data.split('_')
    amount, product = edit_to_cart(command, user, product_id)
    message = f'{product} - {amount} шт.'
    if amount > 0:
        buttons = ([InlineKeyboardButton(text='Добавить', callback_data=f'add-cart_{product_id}'),
                    InlineKeyboardButton(text='Убрать', callback_data=f'remove-cart_{product_id}')],)
        keyboard_edit = InlineKeyboardMarkup([button for button in buttons])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=message,
                                      reply_markup=keyboard_edit)
    else:
        keyboard_edit = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Добавить', callback_data=f'add-cart_{product_id}')]])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=message,
                                      reply_markup=keyboard_edit)


edit_cart_handler = CallbackQueryHandler(edit_cart, pattern="^" + str('add-cart_'))
dispatcher.add_handler(edit_cart_handler)

catalog_handler = CallbackQueryHandler(edit_cart, pattern="^" + str('remove-cart_'))
dispatcher.add_handler(catalog_handler)


def cart_list(update: Update, context: CallbackContext):
    '''Показать корзину покупателя/ Отмена удаления корзины'''
    user = update.callback_query.message.chat.username
    cart_info = show_cart(user)
    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id,
                               message_id=message_id)
    if len(cart_info) > 0:
        for product in cart_info:
            product_name, amount, price = product
            product_id = get_product_id(product_name)
            buttons = ([InlineKeyboardButton(text='Добавить', callback_data=f'add-cart_{product_id}'),
                        InlineKeyboardButton(text='Убрать', callback_data=f'remove-cart_{product_id}')],)
            keyboard_edit = InlineKeyboardMarkup([button for button in buttons])
            message = f'{product_name} - {amount} шт. по {price} р.\n'
            context.bot.send_message(chat_id=chat_id,
                                     text=message,
                                     reply_markup=keyboard_edit)

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Обновить', callback_data='cancel-delete-cart')]])

        context.bot.send_message(chat_id=chat_id,
                                 text='Для посчета суммы нажмите обновить',
                                 reply_markup=keyboard)


cart_list_handler = CallbackQueryHandler(cart_list, pattern=str('correct-cart'))
dispatcher.add_handler(cart_list_handler)


def order(update: Update, context: CallbackContext):
    '''Оформить заявку (переслать в канал менеджеров)'''
    db, cur = connect_db()
    order_num = load_last_order(cur)

    call = update.callback_query
    command, cart_price = call.data.split('_')
    order_message = f'Заказ №: {order_num} \n {call.message.text}'
    context.bot.answer_callback_query(callback_query_id=call.id,
                                      text=f'Ваш заказ номер {order_num} принят, ожидайте звонка менеджера')
    context.bot.edit_message_text(text=order_message,
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id)
    context.bot.forward_message(chat_id=ORDERS_CHAT_ID,
                                from_chat_id=call.message.chat_id,
                                message_id=call.message.message_id)
    context.bot.edit_message_text(text=f'Ваш номер заказа №: {order_num}',
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id)

    save_order(call.from_user.username, order_num, call.message.text, cart_price)
    save_last_order(db, cur, order_num)


order_cart_handler = CallbackQueryHandler(order, pattern=str('order_'))
dispatcher.add_handler(order_cart_handler)


def delete_cart(update: Update, context: CallbackContext):
    '''Очистить корзину'''
    call = update.callback_query

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
    '''Подтвердить удаление корзины'''

    call = update.callback_query
    db_delete_cart(call.message.chat.username)
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    context.bot.answer_callback_query(callback_query_id=call.id, text=f'Корзина очищена')


accept_cart_handler = CallbackQueryHandler(accept_delete_cart, pattern=str('accept-delete-cart'))
dispatcher.add_handler(accept_cart_handler)


def remove_bot_message(update: Update, context: CallbackContext):
    '''Закрыть сообщение бота'''
    call = update.callback_query
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)


remove_message = CallbackQueryHandler(remove_bot_message, pattern=str('remove-message'))
dispatcher.add_handler(remove_message)


def orders_history(update: Update, context: CallbackContext):
    '''Вызов истории покупок'''
    user = update.message.from_user.username
    orders = get_user_orders(user)
    text = ''
    for order in orders:
        text += f'''Заказ № {order[2]} \n {order[3]} \n {"_" * 20} \n'''

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=text,
                             reply_markup=keyboard)


orders_history_handler = MessageHandler(Filters.text('Мои заказы'), orders_history)
dispatcher.add_handler(orders_history_handler)


def unknown(update: Update, context: CallbackContext):
    '''Неизветсные команды'''
    context.bot.send_message(chat_id=update.effective_chat.id, text="Я не знаю такой команды")


unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

if __name__ == '__main__':
    updater.start_polling()
