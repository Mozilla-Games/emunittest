import subprocess, sys

def run_process(cmd):
  try:
    return subprocess.call(cmd)
  except KeyboardInterrupt, e:
    sys.exit(1)
  except:
    pass

emrun_args = sys.argv[1:]
page_args = []
if '--' in emrun_args:
  i = emrun_args.index('--')
  page_args = emrun_args[i+1:]
  emrun_args = emrun_args[:i]
cmd = ['python', 'emrun.py'] + emrun_args + ['--safe_firefox_profile', 'index.html', 'autorun'] + page_args
print str(cmd)
returncode = run_process(cmd)
sys.exit(returncode)
