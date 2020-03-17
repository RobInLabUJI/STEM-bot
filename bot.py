#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from Listener import Listener
from callbacks import start_cb, help_cb, error_cb, text_handler

import sys, yaml

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('usage: bot_server.py config_file')
		sys.exit(0)
	else:
		config_file = sys.argv[1]

	with open(config_file, 'r') as ymlfile:
	    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

	updater = Updater(cfg['token'], use_context=True)

	dp = updater.dispatcher

	dp.add_handler(CommandHandler("start", start_cb))
	dp.add_handler(CommandHandler("help", help_cb))
	dp.add_handler(MessageHandler(Filters.text, text_handler))
	dp.add_error_handler(error_cb)

	updater.start_polling()
	updater.idle()
