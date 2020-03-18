import config

import base64, jupyter_client, os

from io import BytesIO
from threading import Timer

from Listener import Listener

def start_cb(update, context):
        tgid = update.message.from_user.id
        kernel = config.kernel
        if tgid in config.kernel_dict:
            update.message.reply_text('Kernel already started')
        elif config.num_kernels >=50:
            update.message.reply_text('Too many users, please come back later!')
        else:
            config.num_kernels += 1
            update.message.reply_text('Starting kernel...')
            wd = '/home/jovyan/work/' + str(tgid)
            os.makedirs(wd, exist_ok=True)
            if kernel=='python':
                pass
            elif kernel == 'R':
                rlibd = wd + '/R-libs'
                os.makedirs(rlibd, exist_ok=True)
            elif kernel == 'octave':
                pkgd = wd + '/octave_packages'
                os.makedirs(pkgd, exist_ok=True)

            rwd = wd

            km = jupyter_client.KernelManager(kernel_name = config.kernel_name[kernel])
            km.start_kernel(cwd=rwd)
            cl = km.blocking_client()
            _init_commands(cl, rwd, kernel)
            t = Timer(config.timer_value, stop_kernel, [tgid])
            t.start()
            config.kernel_dict[tgid] = (km, cl, t, kernel)
            update.message.reply_text(kernel + ' is ready!')
        
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
        
def restart_cb(update, context):
        tgid = update.message.from_user.id
        kernel = config.kernel
        if tgid in config.kernel_dict:
                update.message.reply_text('Stopping kernel...')
                stop_kernel(tgid)
        start_cb(update, context)

def stop_kernel(tgid):
    (km, cl, t, kernel) = config.kernel_dict[tgid]
    t.cancel()
    km.shutdown_kernel()
    #km.shutdown_kernel(now=True)
    config.kernel_dict.pop(tgid, None)
  
def help_cb(update, context):
    tgid = update.message.from_user.id
    (km, cl, t, kernel) = config.kernel_dict[tgid]
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

def error_cb(update, context):
    """Log Errors caused by Updates."""
    config.logger.warning('Update "%s" caused error "%s"', update, context.error)
    
def text_handler(update, context):
    tgid = update.message.from_user.id
    if not tgid in config.kernel_dict:
        update.message.reply_text('Kernel not running, please use command /start')
    else:
        (km, cl, t, kernel) = config.kernel_dict[tgid]
        if not km.is_alive():
            update.message.reply_text('Kernel not running, please use command /restart')
        else:
            t.cancel()
            t = Timer(config.timer_value, stop_kernel, [tgid])
            t.start()
            config.kernel_dict[tgid] = (km, cl, t, kernel)
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

def signal_handler(signum, frame):
    print('Stopping kernels...')
    for tgid in config.kernel_dict:
        print(tgid)
        (km, cl, t, kernel) = config.kernel_dict[tgid]
        km.shutdown_kernel()
        #km.shutdown_kernel(now=True)
    print('Done.')
