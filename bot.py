from typing import List
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from decouple import config

from helper import round_time, ALLOWED_SETTINGS, ALLOWED_FILTERS, ITERABLE_FILTERS, HELP_TEXT
from datetime import timedelta
from storage import UsersDB, RSSFeed
from rss_parser import JobPost, RSSParser

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


BOT_TOKEN = config("TOKEN")

users_db = UsersDB()
updater = Updater(token=BOT_TOKEN)
dispatcher = updater.dispatcher
job_queue = updater.job_queue

# Handlers methods


# Callback method to run every 10 minutes looking for jobs
def look_for_jobs_cb(context: CallbackContext):
    chat_id = context.job.context
    user_obj = users_db.get_user(chat_id)
    rss_list: List[RSSFeed] = users_db.get_user_rss(chat_id)
    for rss in rss_list:
        posts: List[JobPost] = RSSParser(rss["url"], user_obj).parse_rss()
        posts = posts[::-1]
        for post in posts:
            message = f"[{rss.name}]\n\n{str(post)}"
            context.bot.send_message(chat_id=chat_id, text=message)


def start(update: telegram.Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Hi! I'm upwork bot, ready to help you find jobs without wasting time!")


def add_rss(update: telegram.Update, context: CallbackContext):
    try:
        rss_url = context.args[0]
        rss_name = ' '.join(context.args[1:])
        rss_feed = RSSFeed(rss_name, rss_url)
        users_db.add_user_rss(update.message.chat_id, rss_feed)
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Added RSS feed!")
        # context.job_queue.run_repeating(
        #    look_for_jobs_cb, interval=timedelta(minutes=15), first=5, context=update.message.chat_id)
        context.job_queue.run_repeating(
            look_for_jobs_cb, interval=timedelta(minutes=15), first=round_time(), context=update.message.chat_id)

    except IndexError:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid input, please use /add_rss <rss_url> <rss_name>")


def list_rss(update: telegram.Update, context: CallbackContext):
    rss_list = users_db.get_user_rss(update.message.chat_id)
    if rss_list is None or not rss_list:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="No RSS feed to show, use /add_rss to add some first!")
        return
    for rss in rss_list:
        message = f"[{rss['name']}]: {rss['url']}"
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=message)


def set_settings_cb(update: telegram.Update, context: CallbackContext):
    try:
        keyword = context.args[0].lower()
        value = context.args[1]
        if keyword not in ALLOWED_SETTINGS:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Invalid settings keyword, allowed keywords are: [{', '.join(ALLOWED_SETTINGS)}]")
            return
    except IndexError:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid input, please use /set <key_word> <value>")
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Allowed keywords are: [{', '.join(ALLOWED_SETTINGS)}]")
        return
    users_db.set_user_settings(update.message.chat_id, keyword, value)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Successfully set {keyword} = {value}!")


def list_settings_cb(update: telegram.Update, context: CallbackContext):
    settings = users_db.get_user_settings(update.message.chat_id)
    if not settings:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"No settings are set yet, please use /set <key_word> <value>")
        return
    message = "[SETTINGS]\n"
    message += "\n".join([f"{k} = {v}" for k, v in settings.items()])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=message)


def add_filter_cb(update: telegram.Update, context: CallbackContext):
    try:
        keyword = context.args[0].lower()
        if keyword in ITERABLE_FILTERS:
            value = ' '.join(context.args[1:]).split(',')
            value = [x.strip() for x in value]
        else:
            value = context.args[1]
        if keyword not in ALLOWED_FILTERS:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Invalid filter keyword, allowed keywords are: [{', '.join(ALLOWED_FILTERS)}]")
            return
    except IndexError:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid input, please use /add_filter <key_word> <value>")
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Allowed keywords are: [{', '.join(ALLOWED_FILTERS)}]")
        return
    users_db.set_user_filter(update.message.chat_id, keyword, value)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Successfully set filter {keyword} = {value}!")


def list_filters_cb(update: telegram.Update, context: CallbackContext):
    filters = users_db.get_user_filters(update.message.chat_id)
    if not filters:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"No filters are set yet, please use /add_filter <key_word> <value>")
        return
    message = "[FILTERS]\n"
    message += "\n".join([f"{k} = {v}" for k, v in filters.items()])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=message)


def help_me_cb(update: telegram.Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=HELP_TEXT, parse_mode=telegram.ParseMode.MARKDOWN)


def unknown_command(update: telegram.Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Sorry, I didn't understand that command!")


# Handlers
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# RSS handlers
add_rss_handler = CommandHandler('add_rss', add_rss)
list_rss_handler = CommandHandler('list_rss', list_rss)

dispatcher.add_handler(add_rss_handler)
dispatcher.add_handler(list_rss_handler)

# User settings and filters
settings_handler = CommandHandler('set', set_settings_cb)
list_settings_handler = CommandHandler('settings', list_settings_cb)

add_filter_handler = CommandHandler('add_filter', add_filter_cb)
list_filter_handler = CommandHandler('filters', list_filters_cb)

dispatcher.add_handler(settings_handler)
dispatcher.add_handler(list_settings_handler)
dispatcher.add_handler(add_filter_handler)
dispatcher.add_handler(list_filter_handler)

# HEEEEEEEEEEEEEELP
help_handler = CommandHandler('help', help_me_cb)
dispatcher.add_handler(help_handler)


unknown_command_handler = MessageHandler(Filters.command, unknown_command)
dispatcher.add_handler(unknown_command_handler)


if __name__ == '__main__':
    # Init jobs
    for user in users_db.get_all_users():
        if user["id"] == 1:
            continue
        job_queue.run_repeating(look_for_jobs_cb, interval=timedelta(
            minutes=15), first=round_time(), context=user["id"])

    updater.start_polling(poll_interval=0.2, timeout=10)
    updater.idle()
