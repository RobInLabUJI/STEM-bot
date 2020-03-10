#!/usr/bin/env python3

import telegram.ext as tgext
from telegram.ext.dispatcher import run_async
from telegram.ext import CallbackContext
from telegram import Update

import rpyc, subprocess
import base64, datetime, logging, os, re, socket, sys, yaml

from time import sleep
from io import BytesIO
from threading import Timer

class Listener():
	def __init__(self, kernel):
		self.text = ''
		self.ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
		self.img_data = None
		self.kernel = kernel

	def escape_ansi_text(self):
		return self.ansi_escape.sub('', self.text)

	def output_cb(self, msg):
		msg_type = msg['msg_type']
		content = msg['content']
		if msg_type == 'execute_result': # or msg_type == 'display_data':
			self.text += content['data']['text/plain']
		elif msg_type == 'display_data' and self.kernel == 'R' and 'text/plain' in content['data']:
			if content['data']['text/plain'] != 'plot without title':
				self.text += content['data']['text/plain']
		elif msg_type == 'stream':
			self.text += content['text']
		elif msg_type == 'error':
			for line in content['traceback']:
				self.text += line
				self.text += '\n'
		if 'data' in content and 'image/png' in content['data']:
			self.img_data = content['data']['image/png']
		else:
			pass

@run_async
def text_handler(update: Update, context: CallbackContext):
	tgid = update.message.from_user.id
	write_log(tgid, update.message.text)
	if not tgid in kernel_dict:
		update.message.reply_text('Kernel not running, please use command /start')
	else:
		(km, cl, jc, cnn, t, kernel) = kernel_dict[tgid]
		if not km.is_alive():
			update.message.reply_text('Kernel not running, please use command /restart')
		else:
			t.cancel()
			t = Timer(timer_value, stop_container, [tgid])
			t.start()
			kernel_dict[tgid] = (km, cl, jc, cnn, t, kernel)
			li = Listener(kernel)
			try:
				timeout = 5.0
				if kernel == 'octave' and update.message.text[:11] == 'pkg install':
					timeout = 60.0
				reply = cl.execute_interactive(update.message.text, allow_stdin=False, 
							       timeout=timeout, output_hook=li.output_cb)
			except TimeoutError:
				context.bot.send_message( chat_id=update.message.chat_id, text='Timeout waiting for reply' )
			if li.text:
				text = li.escape_ansi_text()
				if len(text) <= 4096:
					context.bot.send_message( chat_id=update.message.chat_id, text=text )
				else:
					context.bot.send_message( chat_id=update.message.chat_id, text=text[:4092]+'\n...' )
			if li.img_data:
				image = base64.b64decode(li.img_data)
				bio = BytesIO()
				bio.name = 'image.png'
				bio.write(image)
				bio.seek(0)
				context.bot.send_photo(chat_id=update.message.chat_id, photo=bio)	

def error_handler(update: Update, context: CallbackContext):
	logger.warning('Update "%s" caused error "%s"' % (update, context.error))

def _init_commands(cl, wd, kernel):
	if kernel == 'python':
		cl.execute_interactive("%matplotlib inline")
	elif kernel == 'R':
		rlibd = wd + '/R-libs'
		cl.execute_interactive(".libPaths('%s')" % rlibd)
	elif kernel == 'octave':
		pkgd = 'octave_packages'
		cl.execute_interactive("pkg prefix %s %s" % (pkgd, pkgd))
		cl.execute_interactive("pkg local_list %s/.octave_packages" % pkgd)

@run_async
def restart_handler(update: Update, context: CallbackContext):
	tgid = update.message.from_user.id
	write_log(tgid, '/restart')
	if not tgid in kernel_dict:
		update.message.reply_text('Kernel not running, please use command /start')
	else:
		(km, cl, jc, cnn, t, kernel) = kernel_dict[tgid]
		t.cancel()
		update.message.reply_text('Restarting kernel...')
		rwd = '/home/jovyan/workspace'
		km.restart_kernel(cwd=rwd)
		cl = km.blocking_client()
		_init_commands(cl, rwd, kernel)
		t = Timer(timer_value, stop_container, [tgid])
		t.start()
		kernel_dict[tgid] = (km, cl, jc, cnn, t, kernel)
		update.message.reply_text('Ready!')

def write_log(tgid, s):
	filename = 'log/' + str(tgid) + '.log'
	dt = datetime.datetime.now()
	with open(filename, "a") as logfile:
		logfile.write('### ' + dt.isoformat())
		logfile.write('\n')
		logfile.write(s)
		logfile.write('\n')

def stop_container(tgid):
	global num_kernels
	kernel_dict.pop(tgid)
	num_kernels -= 1
	container = cfg['image']+'_'+str(tgid)
	subprocess.Popen(["docker", "container", "stop", container])

@run_async
def start_handler(update: Update, context: CallbackContext):
	global num_kernels
	tgid = update.message.from_user.id
	kernel = context.args[0]
	write_log(tgid, '/start '+ kernel)
	if tgid in kernel_dict:
		update.message.reply_text('Kernel already started')
	elif num_kernels >=5:
		update.message.reply_text('Too many users, please come back later!')
	else:
		num_kernels += 1
		update.message.reply_text('Starting kernel...')
		wd = '/root/workspace/' + str(tgid)
		os.makedirs(wd, exist_ok=True)
		if kernel == 'python':
			pass
		elif kernel == 'R':
			rlibd = wd + '/R-libs'
			os.makedirs(rlibd, exist_ok=True)
		elif kernel == 'octave':
			pkgd = wd + '/octave_packages'
			os.makedirs(pkgd, exist_ok=True)
		
		rwd = '/home/jovyan/workspace'
		#container = cfg['image']+'_'+str(tgid)
		#subprocess.Popen(["docker", "run", "-it", "--rm", "-e", "18812", \
		#		  "-v", wd+":"+rwd+":rw", "--name", container, cfg['image'], \
		#		  "start.sh", "/opt/conda/bin/rpyc_classic.py"])
		#sleep(3)
		#out = subprocess.check_output(["docker", "inspect", "-f", "'{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'", container])
		#ip = out.decode("utf-8")[1:-2]
		ip = socket.gethostbyname("stem-bot_jupyter_1")

		t = Timer(timer_value, stop_container, [tgid])
		t.start()
		conn = rpyc.classic.connect(ip)
		jupyter_client = conn.modules['jupyter_client']

		if kernel=='R':
			kernel_name = 'ir'
		else:
			kernel_name = kernel
		km = jupyter_client.KernelManager(kernel_name = kernel_name)
		km.start_kernel(cwd=rwd)
		cl = km.blocking_client()
		_init_commands(cl, rwd, kernel)
		kernel_dict[tgid] = (km, cl, jupyter_client, conn, t, kernel)
		update.message.reply_text(kernel + ' is ready!')

@run_async
def help_handler(update: Update, context: CallbackContext):
	tgid = update.message.from_user.id
	(km, cl, jc, cnn, t, kernel) = kernel_dict[tgid]
	write_log(tgid, '/help')
	if kernel == 'python':
		s = 'Python Help\n'
		s += 'https://www.python.org/about/help/'
	elif kernel == 'octave':
		s = 'Octave Help\n'
		s += 'https://www.gnu.org/software/octave/support.html'
	elif kernel == 'R':
		s = 'R Help\n'
		s += 'https://www.r-project.org/help.html'
	else:
		s = 'No help available for this kernel yet'
	update.message.reply_text(s)
 
if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('usage: bot_server.py config_file')
		sys.exit(0)
	else:
		config_file = sys.argv[1]

	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
	logger = logging.getLogger(__name__)

	with open(config_file, 'r') as ymlfile:
	    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

	num_kernels = 0
	kernel_dict = {}
	timer_value = 600.0 #seconds

	updater = tgext.Updater(cfg['token'], use_context=True)
	dp = updater.dispatcher

	dp.add_handler(tgext.CommandHandler('start', start_handler))
	dp.add_handler(tgext.CommandHandler('restart', restart_handler))
	dp.add_handler(tgext.CommandHandler('help',  help_handler))
	dp.add_handler(tgext.MessageHandler(tgext.Filters.text,  text_handler))
	dp.add_error_handler(error_handler)

	updater.start_polling()
	updater.idle()