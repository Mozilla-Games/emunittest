import subprocess, time, sys, os, platform, zipfile, tarfile, shutil

WINDOWS = False
LINUX = False
OSX = False
if os.name == 'nt':
  WINDOWS = True
elif platform.system() == 'Linux':
  LINUX = True
elif platform.mac_ver()[0] != '':
  OSX = True

one_day_in_seconds = 60*60*24

# Counts the number of browser runs that failed. This will be the process exit code.
num_failed_runs = 0

# If set, the uncompressed application directory is not deleted after the benchmark has run
NO_DELETE = False

# If set, the downloaded application zip file is not deleted after the benchmark has run
NO_DELETE_ZIP = False

# Specifies the number of times each test is repeated.
NUM_TIMES = 1

ANDROID = False

# Directory where all temporary browsers are downloaded and unzipped to
BROWSERS_PATH = '.browsers'

BENCHMARKS_DONE_PATH = '.benchmarks.done'

for i in range(1, len(sys.argv)):
  if sys.argv[i] == '--no_delete':
    NO_DELETE = True
    sys.argv[i] = ''
  elif sys.argv[i] == '--no_delete_zip':
    NO_DELETE_ZIP = True
    sys.argv[i] = ''
  elif sys.argv[i].startswith('--numtimes='):
    NUM_TIMES = int(sys.argv[i][len('--numtimes='):])
    sys.argv[i] = ''
  elif sys.argv[i] == '--android':
    print 'Running benchmark on an Android device.'
    ANDROID = True
    BROWSERS_PATH = '.browsers.android'
    BENCHMARKS_DONE_PATH = '.benchmarks.done.android'
    sys.argv[i] = ''
  elif sys.argv[i].startswith('-'):
    print >> sys.stderr, 'Unrecognized command line parameter ' + sys.argv[i] + '!'
    sys.exit(1)

sys.argv = filter(lambda x: len(x) > 0, sys.argv)

# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
  print('mkdir_p(' + path + ')')
  if os.path.exists(path):
    return
  try:
    os.makedirs(path)
  except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else: raise

def num_files_in_directory(path):
  if not os.path.isdir(path):
    return 0
  return len([name for name in os.listdir(path) if os.path.exists(os.path.join(path, name))])

# http://pythonicprose.blogspot.fi/2009/10/python-extract-targz-archive.html
def untargz(source_filename, dest_dir, unpack_even_if_exists=False):
  print('untargz(source_filename=' + source_filename + ', dest_dir=' + dest_dir + ')')
  if not unpack_even_if_exists and num_files_in_directory(dest_dir) > 0:
    print("File '" + source_filename + "' has already been unpacked, skipping.")
    return True
  print("Unpacking '" + source_filename + "' to '" + dest_dir + "'")
  mkdir_p(dest_dir)
  run(['tar', '-xvf', source_filename, '--strip', '1', '--directory', dest_dir])
  return True

# http://stackoverflow.com/questions/12886768/simple-way-to-unzip-file-in-python-on-all-oses
def unzip(source_filename, dest_dir, unpack_even_if_exists=False):
  print('unzip(source_filename=' + source_filename + ', dest_dir=' + dest_dir + ')')
  if not unpack_even_if_exists and num_files_in_directory(dest_dir) > 0:
    print("File '" + source_filename + "' has already been unpacked, skipping.")
    return True
  print("Unpacking '" + source_filename + "' to '" + dest_dir + "'")
#  mkdir_p(dest_dir)
  common_subdir = None
  try:
    with zipfile.ZipFile(source_filename) as zf:
      # Implement '--strip 1' behavior to unzipping by testing if all the files in the zip reside in a common subdirectory, and if so,
      # we move the output tree at the end of uncompression step.
      for member in zf.infolist():
        words = member.filename.split('/')
        if len(words) > 1: # If there is a directory component?
          if common_subdir == None:
            common_subdir = words[0]
          elif common_subdir != words[0]:
            common_subdir = ''
            break

      unzip_to_dir = dest_dir
      if common_subdir:
        unzip_to_dir = os.path.join('/'.join(dest_dir.split('/')[:-1]), 'unzip_temp')

      # Now do the actual decompress.
      for member in zf.infolist():
        # Path traversal defense copied from
        # http://hg.python.org/cpython/file/tip/Lib/http/server.py#l789
        words = member.filename.split('/')
        path = unzip_to_dir
        for word in words[:-1]:
          drive, word = os.path.splitdrive(word)
          head, word = os.path.split(word)
          if word in (os.curdir, os.pardir, ''): continue
          path = os.path.join(path, word)
        zf.extract(member, unzip_to_dir)

      if common_subdir:
        try:
          if os.path.exists(dest_dir):
            remove_tree(dest_dir)
        except:
          pass
        shutil.copytree(os.path.join(unzip_to_dir, common_subdir), dest_dir)
        try:
          remove_tree(unzip_to_dir)
        except:
          pass
  except zipfile.BadZipfile as e:
    print("Unzipping file '" + source_filename + "' failed due to reason: " + str(e) + "! Removing the corrupted zip file.")
    rmfile(source_filename)
    return False
  except Exception as e:
    print("Unzipping file '" + source_filename + "' failed due to reason: " + str(e))
    return False

  return True

def run(cmd):
  print str(cmd)
  return subprocess.check_call(cmd)

def run_get_output(cmd):
  print str(cmd)
  return subprocess.check_output(cmd)

def download_browser_zip(download_path, date):
  if download_path != '.': raise Exception("TODO: this needs to be cwd for now")

  existing_items = os.listdir(download_path)
  if ANDROID:
    print 'Downloading Firefox Android browser for date ' + date
    cmd = ['mozdownload', '--version=latest', '--type=daily', '--date='+date, '--application=fennec', '-p', 'android-api-15']
  else:
    print 'Downloading Firefox browser for date ' + date
    cmd = ['mozdownload', '--version=latest', '--type=daily', '--date='+date]
    if WINDOWS:
      cmd += ['--extension', 'zip']

  try:
    run(cmd)
  except OSError, e:
    if e[0] == 2:
      print 'Failed to run the "mozdownload" utility! Please install mozdownload, (often this can be done by running "pip install -U mozdownload")'
      sys.exit(1)
    raise e

  new_items = [f for f in os.listdir(download_path) if f not in existing_items]
  if len(new_items) == 0:
    raise Exception('Failed to download browser for date ' + date + '!')
  browser_zip = new_items[0]
  mkdir_p(BROWSERS_PATH)
  moved_browser_zip = os.path.join(BROWSERS_PATH, browser_zip)
  shutil.move(browser_zip, moved_browser_zip)
  return moved_browser_zip

def uncompress_browser_zip(browser_zip):
  print 'Uncompressing Firefox browser ' + browser_zip
  if OSX:
    new_browser_root = browser_zip.replace('.dmg', '.app')
    print 'Browser .dmg name: ' + browser_zip
    run(['hdiutil', 'attach', browser_zip, '-nobrowse', '-noautoopen'])
    run(['cp', '-r', '/Volumes/Nightly/FirefoxNightly.app', new_browser_root])
    run(['hdiutil', 'detach', '/Volumes/Nightly'])
  elif WINDOWS:
    new_browser_root = browser_zip.replace('.zip', '')
    unzip(browser_zip, new_browser_root)
  elif LINUX:
    new_browser_root = browser_zip.replace('.tar.bz2', '')
    untargz(browser_zip, new_browser_root)
  else: raise Exception("unknown OS")

  if not NO_DELETE_ZIP:
    print 'Deleting ' + browser_zip + ' to save space'
    os.remove(browser_zip) # Don't need the .dmg/.zip/.tar.bz2 file lying around anymore
  return new_browser_root

def find_existing_browser_zip(download_path, date):
  existing_items = [f for f in os.listdir(download_path) if f.startswith(date) and 'firefox' in f]
  for x in existing_items:
    if OSX:
      if os.path.isfile(x) and x.endswith('.dmg'):
        return x
    elif WINDOWS:
      if os.path.isfile(x) and x.endswith('.zip'):
        return x
    elif LINUX:
      if os.path.isfile(x) and x.endswith('.tar.bz2'):
        return x
    else:
      raise Exception("Unknown OS")
  return None

def find_existing_browser_app(download_path, date):
  existing_items = [f for f in os.listdir(download_path) if f.startswith(date) and 'firefox' in f]
  for x in existing_items:
    if OSX:
      if x.endswith('.app'):
        return x
    elif WINDOWS or LINUX:
      if os.path.isdir(x):
        return x
    else:
      raise Exception("Unknown OS")
  return None

def path_to_browser_exe(browser_app_dir):
  if OSX:
    return os.path.join(browser_app_dir, 'Contents/MacOS/firefox')
  elif WINDOWS:
    return os.path.join(browser_app_dir, 'firefox.exe')
  elif LINUX:
    return os.path.join(browser_app_dir, 'firefox')
  else:
    raise Exception("Unknown OS")
  return None

def android_uninstall_firefox_nightly():
  cmd = ['adb', 'uninstall', 'org.mozilla.fennec']
  run(cmd)

def android_install_firefox_nightly(path_to_apk):
  cmd = ['adb', 'install', path_to_apk]
  run(cmd)

def run_benchmark(date):
  global num_failed_runs

  print date + ': running benchmark'

  download_path = '.'

  if not os.path.exists(BENCHMARKS_DONE_PATH):
    os.makedirs(BENCHMARKS_DONE_PATH)

  browser_app = ''

  try:
    if ANDROID:
      browser_exe = 'firefox_nightly'
      browser_zip = download_browser_zip(download_path, date)
      browser_app = browser_zip

      android_uninstall_firefox_nightly()
      android_install_firefox_nightly(browser_app)
    else:
      #existing_files = [f for f in os.listdir(download_path) if os.path.isfile(os.path.join(download_path, f))]
      browser_app = find_existing_browser_app(download_path, date)#[x for x in existing_files if x.startswith(date) and (x.endswith('.dmg') or x.endswith('.app'))]
      if not browser_app:
        browser_zip = find_existing_browser_zip(download_path, date)
        if not browser_zip:
          browser_zip = download_browser_zip(download_path, date)

        browser_app = uncompress_browser_zip(browser_zip)

      browser_exe = path_to_browser_exe(browser_app)

    print 'Browser root directory: ' + browser_app
    print 'Browser exe file: ' + browser_exe

    android = ['--android'] if ANDROID else []

    browser_info = run_get_output(['python', 'emrun.py', '--browser_info', '--browser', browser_exe] + android)
    print browser_info

    page_args = ['novsync', 'uploadResults']
    if not ANDROID: page_args += ['numtimes=' + str(NUM_TIMES)]
    cmd = ['python', 'run.py', '--browser=' + browser_exe, '--silence_timeout=300', '--kill_exit'] + android + ['--'] + page_args
    run(cmd)

    done_file = os.path.join(BENCHMARKS_DONE_PATH, date + '.done.txt')
    print 'Browser run successfully done, flagging it done in the record file "' + done_file + '"'
    open(done_file, 'w').write('done on ' + time.strftime("%c"))
  except Exception, e:
    print >> sys.stderr, 'Browser run failed with error: ' + str(e)
    num_failed_runs += 1

    failed_file = os.path.join(BENCHMARKS_DONE_PATH, date + '.failed.txt')
    print >> sys.stderr, 'Flagging the run as failure in the record file "' + failed_file + '"'
    open(failed_file, 'w').write('failed on ' + time.strftime("%c") + ', error:\n' + str(e))

  if not NO_DELETE:
    if 'firefox' in browser_app:
      print 'Deleting browser app directory to save space'
      shutil.rmtree(browser_app, ignore_errors=True) # Save space by removing the .app directory

def run_n_most_recent_nightlies(n, latest_untested=False):
  cur_time = time.time()
  cur_time -= one_day_in_seconds # Workaround if the local time might be ahead that a build for the given day has not been built yet
  if ANDROID: cur_time -= one_day_in_seconds # Android builds seem to lack behind even more
  num_tested = 0
  while num_tested < n:
    cur_date = time.strftime('%Y-%m-%d', time.gmtime(cur_time))
    done_exists = os.path.isfile(os.path.join(BENCHMARKS_DONE_PATH, cur_date + '.done.txt'))
    failed_exists = os.path.isfile(os.path.join(BENCHMARKS_DONE_PATH, cur_date + '.failed.txt'))
    if not done_exists and not failed_exists:
      try:
        run_benchmark(cur_date)
      finally:
        num_tested += 1 # If we fail, always count as having tested this (but try older one next)
    else:
      if done_exists:
        print cur_date + ': skipped, benchmark already run (success)'
      if failed_exists:
        print cur_date + ': skipped, benchmark already run (failure)'
      if not latest_untested: num_tested += 1
    cur_time -= one_day_in_seconds

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print 'This script downloads Nightly Firefox, unpacks it, and runs the emunittest benchmark on the uncompressed browser file'
    print 'Usage: python ' + sys.argv[0] + ' latest|latest_untested|all|all_untested'
    print ' '
    print '"python ' + sys.argv[0] + ' latest" downloads the most recent mozilla-central and runs the suite on it.'
    print '"python ' + sys.argv[0] + ' latest_untested" downloads the most recent mozilla-central you have not yet finished the suite on, and runs the suite on it.'
    print '"python ' + sys.argv[0] + ' all" downloads the 180 most recent mozilla-central builds starting from today and runs the suite on each of them.'
    print '"python ' + sys.argv[0] + ' all_untested" downloads the 180 most recent yet untested mozilla-central builds starting from today and runs the suite on each of them.'
    sys.exit(1)

  if sys.argv[1] == 'all':
    run_n_most_recent_nightlies(180)
  elif sys.argv[1] == 'all_untested':
    run_n_most_recent_nightlies(180, latest_untested=True)
  elif sys.argv[1] == 'latest_untested':
    run_n_most_recent_nightlies(1, latest_untested=True)
  elif sys.argv[1] == 'latest':
    run_n_most_recent_nightlies(1)
  else:
    print 'Unrecognized option ' + sys.argv[1] + '!'
    sys.exit(1)
  print 'benchmark_firefox.py finished. Process return code: ' + str(num_failed_runs)
  sys.exit(num_failed_runs)
