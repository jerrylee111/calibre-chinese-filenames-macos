import os
import sys
from pathlib import Path

sys.argv = ['calibre']

from calibre.utils.config import dynamic
dynamic.set('welcome_wizard_was_run', True)
import calibre.utils.ipc as ipc
ipc.gui_socket_address = lambda: '/tmp/calibre-chinese-packaging-test.sock'
from calibre.gui2 import main
from qt.core import QTimer

real_lock = main.SingleInstance
main.SingleInstance = lambda name: real_lock('chinese-packaging-test-' + name)
real_init = main.init_qt

def init(args):
    app, opts, rest = real_init(args)
    def finish():
        titles = [w.windowTitle() for w in app.topLevelWidgets() if w.isVisible()]
        print('VISIBLE_WINDOWS:', titles, flush=True)
        ok = any('library' in title for title in titles)
        Path(os.environ['CALIBRE_GUI_TEST_RESULT']).write_text('PASS' if ok else 'FAIL')
        app.quit()
    QTimer.singleShot(10000, finish)
    return app, opts, rest

main.init_qt = init
sys.exit(main.main(['calibre', '--with-library=' + os.environ['CALIBRE_GUI_TEST_LIBRARY']]))
