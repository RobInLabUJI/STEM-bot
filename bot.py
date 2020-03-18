#!/usr/bin/env python3

import sys
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import config
from callbacks import start_cb, help_cb, error_cb, restart_cb, text_handler, signal_handler
from Listener import Listener

if __name__ == '__main__':
	if len(sys.argv) < 3:
		print('usage: bot.py <kernel> <TOKEN>')
		sys.exit(0)
	else:
		config.kernel = sys.argv[1]
		token = sys.argv[2]

	updater = Updater(token, use_context=True, user_sig_handler=signal_handler)

	dp = updater.dispatcher

	dp.add_handler(CommandHandler("start", start_cb))
	dp.add_handler(CommandHandler("help", help_cb))
	dp.add_handler(CommandHandler("restart", restart_cb))
	dp.add_handler(MessageHandler(Filters.text, text_handler))
	dp.add_error_handler(error_cb)

	updater.start_polling()
	updater.idle()
