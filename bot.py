#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from Listener import Listener
from callbacks import start_cb, help_cb, error_cb, restart_cb, text_handler, signal_handler

import sys

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('usage: bot.py TOKEN')
		sys.exit(0)
	else:
		token = sys.argv[1]

	updater = Updater(token, use_context=True, user_sig_handler=signal_handler)

	dp = updater.dispatcher

	dp.add_handler(CommandHandler("start", start_cb))
	dp.add_handler(CommandHandler("help", help_cb))
	dp.add_handler(CommandHandler("restart", restart_cb))
	dp.add_handler(MessageHandler(Filters.text, text_handler))
	dp.add_error_handler(error_cb)

	updater.start_polling()
	updater.idle()
