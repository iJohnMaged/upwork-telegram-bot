from typing import List
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from helper import ALLOWED_SETTINGS, ALLOWED_FILTERS, ITERABLE_FILTERS, HELP_TEXT, REPEAT_PERIOD, INITIAL_TUTORIAL
from datetime import timedelta
from storage import UsersDB, RSSFeed
from rss_parser import RSSParser

import os

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

BOT_TOKEN = os.environ.get("TOKEN")
DEV_IDS = [
    int(s.strip())
    for s in os.environ.get("DEVS").split(",")
]

users_db = UsersDB()
updater = Updater(token=BOT_TOKEN)
dispatcher = updater.dispatcher
job_queue = updater.job_queue

# Handlers methods

# Callback method to run every x minutes looking for jobs


def look_for_jobs_cb(context: CallbackContext):
    chat_id = context.job.context
    user_obj = users_db.get_user(chat_id)
    rss_list: List[RSSFeed] = users_db.get_user_rss(chat_id)
    show_summary = user_obj["settings"].get("show_summary", "no")
    show_summary = False if show_summary == "no" else True
    for rss in rss_list:
        posts = RSSParser(rss["url"], user_obj).parse_rss()
        posts = posts[::-1]
        for post in posts:
            message = f"[{rss['name']}]\n\n{post.to_str(show_summary)}"
            context.bot.send_message(chat_id=chat_id, text=message)


def add_job_to_queue(user_id, interval, first):
    job_name = f"job_{user_id}"
    job_queue.run_repeating(
        look_for_jobs_cb,
        interval=interval,
        first=first,
        context=user_id,
        name=job_name,
    )


def start(update: telegram.Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=INITIAL_TUTORIAL, parse_mode='html')

# RSS CALL BACKS


def add_rss(update: telegram.Update, context: CallbackContext):
    try:
        user_id = update.message.chat_id
        rss_url = context.args[0]
        rss_name = ' '.join(context.args[1:])
        rss_feed = RSSFeed(rss_name, rss_url)
        users_db.add_user_rss(user_id, rss_feed)
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Added RSS feed!")
        # context.job_queue.run_repeating(
        #    look_for_jobs_cb, interval=timedelta(minutes=15), first=5, context=user_id)
        job_name = f"job_{user_id}"
        jobs = job_queue.get_jobs_by_name(job_name)
        if len(jobs) == 0:
            add_job_to_queue(
                user_id,
                timedelta(minutes=REPEAT_PERIOD),
                timedelta(minutes=REPEAT_PERIOD)
            )

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


def delete_rss(update: telegram.Update, context: CallbackContext):
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid input, please use /delete_rss <rss_name>")
        return
    rss_name = ' '.join(context.args)
    user_id = update.message.chat_id
    users_db.delete_user_rss(user_id, rss_name)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Deleted {rss_name} RSS")


def pause_updates_cb(update: telegram.Update, context: CallbackContext):
    user_id = update.message.chat_id
    job_name = f"job_{user_id}"
    jobs = job_queue.get_jobs_by_name(job_name)
    for job in jobs:
        job.schedule_removal()
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Paused updates, use /resume to start getting updates again")


def resume_updates_cb(update: telegram.Update, context: CallbackContext):
    user_id = update.message.chat_id
    job_name = f"job_{user_id}"
    jobs = job_queue.get_jobs_by_name(job_name)
    if len(jobs) == 0:
        add_job_to_queue(
            user_id,
            timedelta(minutes=REPEAT_PERIOD),
            timedelta(minutes=REPEAT_PERIOD)
        )
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Resumed updates, use /pause to pause updates when needed")


def set_settings_cb(update: telegram.Update, context: CallbackContext):
    try:
        keyword = context.args[0].lower()
        value = context.args[1].lower()
        if keyword not in ALLOWED_SETTINGS.keys():
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Invalid settings keyword, allowed keywords are: [{', '.join(ALLOWED_SETTINGS.keys())}]")
            return
    except IndexError:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid input, please use /set <key_word> <value>")
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Allowed keywords are: [{', '.join(ALLOWED_SETTINGS.keys())}]")
        return
    valid_values = ALLOWED_SETTINGS[keyword]["values"]
    value = ALLOWED_SETTINGS[keyword]["type"](value)
    if value not in valid_values:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=ALLOWED_SETTINGS[keyword]["error"])
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
    val = users_db.set_user_filter(update.message.chat_id, keyword, value)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Successfully set filter {keyword} = {val}")


def clear_filter_cb(update: telegram.Update, context: CallbackContext):
    try:
        keyword = context.args[0].lower()
        if keyword not in ALLOWED_FILTERS:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Invalid filter keyword, allowed keywords are: [{', '.join(ALLOWED_FILTERS)}]")
            return
    except IndexError:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid input, please use /clear_filter <key_word>")
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Allowed keywords are: [{', '.join(ALLOWED_FILTERS)}]")
        return
    users_db.clear_user_filter(update.message.chat_id, keyword)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Successfully cleared filter {keyword}")


def list_filters_cb(update: telegram.Update, context: CallbackContext):
    filters = users_db.get_user_filters(update.message.chat_id)
    if not filters:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"No filters are set yet, use /add_filter <key_word> <value>")
        return
    message = "[FILTERS]\n"
    message += "\n".join([f"{k} = {v}" for k, v in filters.items()])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=message)


def help_me_cb(update: telegram.Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=HELP_TEXT, parse_mode=telegram.ParseMode.HTML)


def unknown_command(update: telegram.Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Sorry, I didn't understand that command!")


def list_jobs_cb(update: telegram.Update, context: CallbackContext):
    id = update.effective_chat.id
    if id not in DEV_IDS:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="NOT AUTHORIZED")
        return
    for job in job_queue.jobs():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"{job}, REMOVED: {job.removed} NEXT: {job.next_t}")


def run_job_cb(update: telegram.Update, context: CallbackContext):
    id = update.effective_chat.id
    job_name = f"job_{id}"
    jobs = job_queue.get_jobs_by_name(job_name)
    try:
        jobs[0].run(dispatcher)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Update completed")
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Something went wrong, make sure updates are not paused")


def id_cb(update: telegram.Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Your ID: {update.effective_chat.id}")


commands = {
    "start": start,
    "add_rss": add_rss,
    "delete_rss": delete_rss,
    "list_rss": list_rss,
    "set": set_settings_cb,
    "settings": list_settings_cb,
    "add_filter": add_filter_cb,
    "clear_filter": clear_filter_cb,
    "filters": list_filters_cb,
    "pause": pause_updates_cb,
    "resume": resume_updates_cb,
    "jobs": list_jobs_cb,
    "get_jobs": run_job_cb,
    "id": id_cb,
    "help": help_me_cb
}

for k, v in commands.items():
    dispatcher.add_handler(CommandHandler(k, v))

unknown_command_handler = MessageHandler(Filters.command, unknown_command)
dispatcher.add_handler(unknown_command_handler)


if __name__ == '__main__':
    # Init jobs
    for user in users_db.get_all_users():
        if user["id"] == 1:
            continue
        job_name = f"job_{user['id']}"
        add_job_to_queue(
            user["id"],
            timedelta(minutes=REPEAT_PERIOD),
            timedelta(minutes=REPEAT_PERIOD)
        )
    updater.start_polling(poll_interval=0.2, timeout=10)
    updater.idle()
