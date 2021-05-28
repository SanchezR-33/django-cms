#!/usr/bin/env python
# -*- coding: utf-8 -*-
# $Id: setup.py 12629 2020-11-26 13:42:29Z Lavender $
#
# Copyright (c) 2017 Nuwa Information Co., Ltd, All Rights Reserved.
#
# Licensed under the Proprietary License,
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at our web site.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# $Author: Lavender $
# $Date: 2020-11-26 22:42:29 +0900 (週四, 26 十一月 2020) $
# $Revision: 12629 $

import re
import os
import sys
import time
import logging
import shutil
import json
import argparse
import locale
import hashlib
import traceback
import threading
import pkg_resources
import platform

try:
    import colorama 
except Exception as e:
    os.system("pip install colorama==0.4.1")
    import colorama
    
colorama.init()

try:
    from termcolor import colored, cprint
except Exception as e:
    os.system("pip install termcolor==1.1.0")
    from termcolor import colored, cprint
    
try:
    import requests
except Exception as e:
    os.system("pip install requests")
    import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

INTRODUCTION_URL = "https://www.django-cms-themes.com/static/docs"
SETUP_URL = "https://www.django-cms-themes.com/static/product/assets/setup.py"
SETUP_VERSION = "1.1.1"
SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_SUPPORTED_CMS_VERSION = "3.7.4"
CKEDITOR_SETTINGS = \
'''
CKEDITOR_SETTINGS = {
    'language': '',
    'toolbar_CMS': [
        ['cmsplugins',],
       
        ['Source', '-', 'Save', 'NewPage', 'DocProps', 'Preview',
         'Print', '-', ' Templates'],
        ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-',
         'Undo', 'Redo'],
        ['Find', 'Replace', '-', 'SelectAll', '-', 'SpellChecker',
         'Scayt'],
        ['Form', 'Checkbox', 'Radio', 'TextField', 'Textarea', 'Select',
        'Button', 'ImageButton', 'HiddenField'],
        ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript',
        'Superscript', '-', 'RemoveFormat'],
        ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-',
        'Blockquote', 'CreateDiv', '-', 'JustifyLeft', 'JustifyCenter',
        'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl'],
        ['Link', 'Unlink', 'Anchor'],
        ['Image', 'Flash', 'Table', 'HorizontalRule', 'Smiley',
        'SpecialChar', 'PageBreak', 'Iframe'],
        ['Styles', 'Format', 'Font', 'FontSize'],
        ['TextColor', 'BGColor'],
        ['Maximize', 'ShowBlocks', '-', 'About'],
    ],
    'skin': 'moono-lisa',
}
'''

SCHEMA_FIX = '''
    def __enter__(self):
        # Some SQLite schema alterations need foreign key constraints to be
        # disabled. Enforce it here for the duration of the transaction.
        self.connection.disable_constraint_checking()
        self.connection.cursor().execute('PRAGMA legacy_alter_table = ON')
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self.connection.cursor().execute('PRAGMA legacy_alter_table = OFF')
        self.connection.enable_constraint_checking()
'''

SCHEMA_FIX_MD5_1_11 = "08fc81f9012c4a7f94782edc030885e7"
SCHEMA_ORIGIN_MD5_DJANGO_1_11 = "c27ea4f5a250178b0a417b719c40c3a8"
SCHEMA_ORIGIN_DJANGO_1_11 = '''
    def __enter__(self):
        with self.connection.cursor() as c:
            # Some SQLite schema alterations need foreign key constraints to be
            # disabled. This is the default in SQLite but can be changed with a
            # build flag and might change in future, so can't be relied upon.
            # We enforce it here for the duration of the transaction.
            c.execute('PRAGMA foreign_keys')
            self._initial_pragma_fk = c.fetchone()[0]
            c.execute('PRAGMA foreign_keys = 0')
        return super(DatabaseSchemaEditor, self).__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        super(DatabaseSchemaEditor, self).__exit__(exc_type, exc_value, traceback)
        with self.connection.cursor() as c:
            # Restore initial FK setting - PRAGMA values can't be parametrized
            c.execute('PRAGMA foreign_keys = %s' % int(self._initial_pragma_fk))
'''

SCHEMA_FIX_MD5_2_1 = "de8e3a3770fdb73b3f4478e0410ceaf9"
SCHEMA_ORIGIN_MD5_DJANGO_2_1 = "280dba9301b0a827962786c34456ca54"
SCHEMA_ORIGIN_DJANGO_2_1 = '''
    def __enter__(self):
        # Some SQLite schema alterations need foreign key constraints to be
        # disabled. Enforce it here for the duration of the schema edition.
        if not self.connection.disable_constraint_checking():
            raise NotSupportedError(
                'SQLite schema editor cannot be used while foreign key '
                'constraint checks are enabled. Make sure to disable them '
                'before entering a transaction.atomic() context because '
                'SQLite3 does not support disabling them in the middle of '
                'a multi-statement transaction.'
            )
        self.connection.cursor().execute('PRAGMA legacy_alter_table = ON')
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self.connection.cursor().execute('PRAGMA legacy_alter_table = OFF')
        self.connection.enable_constraint_checking()
'''

LOG_URL = "https://www.django-cms-themes.com/log/"

def sendLog(data):
    try:
        data.update({
            "setup_version": SETUP_VERSION,
            "platform_system": str(platform.system()),
            "platform_version": str(platform.version()),
            "platform_uname": str(platform.uname()),
        })
        def job():
            requests.post(LOG_URL, data=data)
        
        t = threading.Thread(target=job)
        t.start()
    except Exception as e:
        # do nothing
        pass
        
def compareVersion(version1, version2):
    version1 = [int(i) for i in version1.split(".")]
    version2 = [int(i) for i in version2.split(".")]
    
    if version1 >= version2:
        return True
    else:
        return False
        
def checkVersion():
    try:
        response = requests.get(SETUP_URL)
        data = response.text
        result = re.findall(r'SETUP_VERSION = "(\d+.\d+.\d+)"', data)
        if result:
            version = result[0]
            
            if not compareVersion(SETUP_VERSION, version):
                logger.warning(colored(
                    ("Your setup.py version is %s, the latest version is %s available. "
                     "Download the latest version from the URL below:") % (SETUP_VERSION, version), 
                    "yellow", attrs=['bold'])
                )
                logger.warning(colored(
                    SETUP_URL, 
                    "white", attrs=['bold'])
                )
                logger.warning(colored(
                    "Or you can download this theme again to make sure use latest setup.py.", 
                    "yellow", attrs=['bold'])
                )
        else:
            raise ValueError("Can't read version from %s" % SETUP_URL)
    except Exception as e:
        sendLog({
            "level": "ERROR",
            "error": str(e),
        })

if not sys.version_info.major == 3:
    logger.warning(
        colored("Python 2.7 are not supported"
                ", please consider upgrade to Python 3", "yellow"))
    sys.exit(1)

def copyToPath(baseDir, templateDir, staticDir, mode):
    import django
    
    if not templateDir:
        templateDir = os.path.join(baseDir, 'templates')
    if not staticDir:
        staticDir = os.path.join(baseDir,'static')
       
    logger.info(colored("-----Start copy templates-----", "yellow"))
    if not os.path.exists(staticDir):
        os.mkdir(staticDir)
    if not os.path.exists(templateDir):
        os.mkdir(templateDir)
    for root, dirs, files in os.walk(os.path.join(SETUP_DIR, "static")):
        for d in dirs:
            index = os.path.join(root, d).index("static") + len("static/")
            path = os.path.join(
                staticDir, os.path.join(os.path.join(root, d))[index:])
            if not os.path.exists(path):
                os.mkdir(path)
               
    if not os.path.exists(os.path.join(baseDir, "fixtures")):
        os.mkdir(os.path.join(baseDir, "fixtures"))
   
    for root, dirs, files in os.walk(SETUP_DIR):
        for f in files:
            if f == 'setup.py':
                continue
            origin = os.path.join(root, f)
           
            if os.path.join(SETUP_DIR, "static") in root:
                index = len(os.path.join(SETUP_DIR, "static")) + 1
                dst = os.path.join(staticDir, origin[index:])
            elif os.path.join(SETUP_DIR, "templates") in root:
                dst = os.path.join(templateDir, f)
            elif os.path.join(SETUP_DIR, "fixtures") in root:
                index = len(os.path.join(SETUP_DIR, "fixtures")) + 1
                dst = os.path.join(baseDir, "fixtures", origin[index:])
            else:
                continue
           
            if os.path.isfile(dst):
                logger.error(
                    colored("%s exists. failed to copy file." % dst, "red"))
            else:
                shutil.copyfile(origin, dst)
                if django.VERSION >= (3, 0) and os.path.join(SETUP_DIR, "templates") in root:
                    with open(dst, 'r') as t:
                        content = t.read()
                    content = content.replace("staticfiles", "static")
                    with open(dst, 'w') as t:
                        t.write(content)
                logger.info("Succeed to copy file to %s." % dst)
   
def findSettings(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            if f == 'settings.py' and "urls.py" in files and "wsgi.py" in files:
                return os.path.join(root, f)
    return None
   
def canAddPlugin(pkgName, pluginName):
    result = 0
   
    try:
        __import__(pluginName)
    except Exception as e:
        result = os.system("pip install %s" % pkgName)
       
    if result != 0:
        return False
    else:
        return True
               
def writeSettings(settingsPath, templateDir, staticDir, hasCmsTemplate, baseDir,
                  cmsVersion, wizard=False, createProject=False):
    logger.info(
        colored("-----Start write and backup settings.py-----", "yellow"))
    def getCMSTemplates():
        templates = []
       
        path = os.path.join(SETUP_DIR, 'templates')
        index = None
               
        for template in os.listdir(path):
            if "_tracking" in template:
                continue
            if template.lower() == 'index.html':
                index = template
                continue
            templates.append((template, template))
       
        if index:
            return [(index, index),] + templates
        else:
            return templates
   
    settingsDir = os.path.dirname(settingsPath)
    bak = os.path.join(settingsDir, 'settings.py.bak')
    if os.path.isfile(bak):
        logger.error(colored("%s exists. failed to backup file." % bak, "red"))
        return 
    shutil.copyfile(settingsPath, bak)
    logger.info(colored("Succeed to backup settings.py to %s." % bak, "yellow"))
               
    with open(settingsPath, 'r') as settings:
        content = settings.read()
               
    with open(settingsPath, 'w') as settings:   
        if hasCmsTemplate:
            content += \
'''
CMS_TEMPLATES = list(CMS_TEMPLATES)
CMS_TEMPLATES += %s
''' % str(getCMSTemplates())
        else:
            content += \
'''
CMS_TEMPLATES = %s
''' % str(getCMSTemplates())
        if not templateDir:
            content = content.replace(
                "'DIRS': []", "'DIRS': [os.path.join(BASE_DIR, 'templates'),]")
           
        if not staticDir:
            content += \
'''
if DEBUG:
    STATICFILES_DIRS = (
        os.path.join(BASE_DIR, 'static'),
    )
else:
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')
'''
        import cms
        import django

        pluginList = []
        requirementList = []
        
        if createProject:
            if wizard:
                if sys.version_info.major == 3:
                    yesOrNo = input(
                        "Do you want to install djangocms_history and "
                        "all ckeditor features?[yes/no]")
                else:
                    yesOrNo = raw_input(
                        "Do you want to install djangocms_history and "
                        "all ckeditor features?[yes/no]")
            else:
                yesOrNo = 'yes'
                
            if yesOrNo == 'yes':
                
                if canAddPlugin(
                    'djangocms-history', 'djangocms_history==0.5.3'):
                    pluginList.append('djangocms_history')
                    requirementList.append('djangocms_history==0.5.3')
                    
                if not django.VERSION >= (2, 0):
                    if canAddPlugin(
                        'djangocms-forms', 'djangocms_forms==0.2.5'):
                        pluginList.append('djangocms_forms')
                        requirementList.append('djangocms_forms==0.2.5')
            
            with open(os.path.join(baseDir, "requirements.txt"), 'a') as reqs:
                reqs.write("\n")
                for r in requirementList:
                    reqs.write("%s\n" % r)
                   
        content += "INSTALLED_APPS += %s" % str(tuple(pluginList))
        content += CKEDITOR_SETTINGS
        
        if int(cmsVersion[0]) == 3 and int(cmsVersion[1]) == 7:
            content = content.replace(
                "'djangocms_bootstrap4.contrib.bootstrap4_picture',", 
                "#'djangocms_bootstrap4.contrib.bootstrap4_picture',")
        settings.write(content)
           
               
    logger.info(colored("Succeed to write settings.py", "yellow"))
               
def loadData(baseDir, language):
    logger.info(colored("-----Start load data-----", "yellow"))
    data = os.path.join(".", 'fixtures', 'initial_data.json')
    result = os.system("%s manage.py migrate" % sys.executable)
    if not result == 0:
        logger.error(colored("Can not migrate db.", "red"))
        return False
       
    result = os.system("%s manage.py loaddata \"%s\"" % (sys.executable, data))
   
    if not result == 0:
        logger.error(colored("Can not loaddata.", "red"))
        return False
   
    from cms.models.pagemodel import Page
    from cms.models.titlemodels import Title
    from cms.models.pluginmodel import CMSPlugin
    from django.db import transaction
   
    @transaction.atomic
    def modifyData():
        for plugin in CMSPlugin.objects.all():
            plugin.language = language
            plugin.save()
        for page in Page.objects.all():
            page.languages = language
            page.save()
        for title in Title.objects.all():
            title.language = language
            title.save()
    modifyData()
       
    return True
    
def fixSchema(schemaPath):
    import django 
    try:
        with open(schemaPath, 'r') as f:
            content = f.read()
            
        if not django.VERSION >= (2, 0):
            SCHEMA_FIX_MD5 = SCHEMA_FIX_MD5_1_11
            SCHEMA_ORIGIN = SCHEMA_ORIGIN_DJANGO_1_11 
            SCHEMA_ORIGIN_MD5 = SCHEMA_ORIGIN_MD5_DJANGO_1_11
        else:
            SCHEMA_FIX_MD5 = SCHEMA_FIX_MD5_2_1
            SCHEMA_ORIGIN = SCHEMA_ORIGIN_DJANGO_2_1
            SCHEMA_ORIGIN_MD5 = SCHEMA_ORIGIN_MD5_DJANGO_2_1
        
        if hashlib.md5(content.encode()).hexdigest() == SCHEMA_ORIGIN_MD5:
            content = content.replace(SCHEMA_ORIGIN, SCHEMA_FIX)
              
        with open(schemaPath, 'w') as f:
            f.write(content)
            
        with open(schemaPath, 'r') as f:
            content = f.read()
    except Exception as e:
        pass
    
def revertSchema(schemaPath):
    import django 
    try:
        with open(schemaPath, 'r') as f:
            content = f.read()
            
        if not django.VERSION >= (2, 0):
            SCHEMA_FIX_MD5 = SCHEMA_FIX_MD5_1_11
            SCHEMA_ORIGIN = SCHEMA_ORIGIN_DJANGO_1_11 
            SCHEMA_ORIGIN_MD5 = SCHEMA_ORIGIN_MD5_DJANGO_1_11
        else:
            SCHEMA_FIX_MD5 = SCHEMA_FIX_MD5_2_1
            SCHEMA_ORIGIN = SCHEMA_ORIGIN_DJANGO_2_1
            SCHEMA_ORIGIN_MD5 = SCHEMA_ORIGIN_MD5_DJANGO_2_1
            
        if hashlib.md5(content.encode()).hexdigest() == SCHEMA_FIX_MD5:
            content = content.replace(SCHEMA_FIX, SCHEMA_ORIGIN)
            
        with open(schemaPath, 'w') as f:
            f.write(content)
    except Exception as e:
        pass
       
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Path to Project')
        parser.add_argument(
            "path", metavar='path', 
            type=str, 
            help="Path to project, default is '.'"
        )
        
        parser.add_argument(
            "--djangoVersion", metavar='djangoVersion', 
            type=str,  nargs='?', default="3.0",
            help="Django version, default is '3.0'"
        )
        
        parser.add_argument(
            "--projectName", metavar='projectName', 
            type=str,  nargs='?',
            help="Django project name."
        )
           
        parser.add_argument(
            '-w', '--wizard', 
            action='store_true',
            help="Run the configuration wizard")   

        args = parser.parse_args()
        cmd = "python setup.py %s" % " ".join(sys.argv[1:])
        
        checkVersion()
        
        if os.path.exists(os.path.join(SETUP_DIR, 'cms')):
            logger.error(colored(
                "In order to use this setup.py normally, the current folder cannot have a folder named 'cms'.", 
                "red", attrs=['bold']
            ))
            sys.exit(0)
        
        try:
            if os.path.isfile(os.path.join(SETUP_DIR, 'MANIFAST.INFO')):
                with open(os.path.join(SETUP_DIR, 'MANIFAST.INFO')) as f:
                    data = json.loads(f.read())
                upc = data['upc']
            else:
                upc = None
        except Exception as e:
            upc = None
            
        projectName = args.projectName
        djangoVersion = args.djangoVersion
        
        djangoVersionTable = {
            '3.0': '<3.1.0,>=3.0',
            '2.2': '<3.0.0,>=2.2',
            '1.11': '<2.0.0,>=1.11',
        }
        if not djangoVersion in djangoVersionTable:
            logger.warning(colored(
                "Django version must be 1.11, 2.2 or 3.0", "yellow"))
            sys.exit(1)
        else:
            djangoVersion = djangoVersionTable[djangoVersion]
            
        try:
            import django
            djangoVersion = "%d.%d.%d" % (
                django.VERSION[0], django.VERSION[1], django.VERSION[2],)
                
            if not "%d.%d" % (django.VERSION[0], django.VERSION[1]) in djangoVersionTable:
                logger.warning(colored(
                    ("Your current Django version is %s which is not fully tested version for Django CMS themes. "
                     "It should work, but if you encounter any problem, we recommend you switch to Django>=2.2,<2.3") % 
                     djangoVersion, 
                    "yellow", attrs=['bold'])
                )
        except Exception as e:
            logger.error(
                colored("Can't find django, try to install.", "yellow"))
            os.system("pip install -U \"django%s\"" % djangoVersion)
            
            import django
            djangoVersion = "%d.%d.%d" % (
                django.VERSION[0], django.VERSION[1], django.VERSION[2],)
        
        # modify django schema.py
        # issue: https://github.com/django/django/pull/10733/commits/c8ffdbe514b55ff5c9a2b8cb8bbdf2d3978c188f
        try:
            schemaPath = pkg_resources.resource_filename(
                'django.db.backends.sqlite3', 'schema.py')
        except Exception as e:
            schemaPath = None
         
        wizard = args.wizard
        mode = 'user'
        
        local = locale.getdefaultlocale()
        if len(local) == 2 and local[0]:
            local = local[0]
        
        if os.path.isfile(os.path.join(SETUP_DIR, 'MANIFAST.INFO')):
            with open(os.path.join(SETUP_DIR, 'MANIFAST.INFO')) as f:
                data = json.loads(f.read())
                
            cmsVersion = data["DjangoCMSVersion"]
        else:
            cmsVersion = '3.7.4'
            
        # default for setup.py
        cmsVersion = '3.7.4'
        
        if cmsVersion.startswith("3.6"):
            installVersion = "1.2.0"
        elif cmsVersion.startswith("3.7"):
            installVersion = "1.2.3"
        else:
            logger.warning(colored(
                "Not support django-cms<3.6", "yellow"))
            sys.exit(1)
        
        # check cms version
        try:
            import cms
            cmsVersion = cms.__version__
            if cmsVersion.split(".") > SETUP_SUPPORTED_CMS_VERSION.split("."):
                logger.warning(colored(
                    ("The version of cms installed in your virtual environment is %s, "
                     "but setup.py only supported django-cms<=%s. "
                     "Try to install django-cms<=%s.") % (
                     cmsVersion, SETUP_SUPPORTED_CMS_VERSION, SETUP_SUPPORTED_CMS_VERSION), "yellow"))
                os.system("pip install \"django-cms<=%s\"" % SETUP_SUPPORTED_CMS_VERSION)
        except Exception as e:
            logger.warning(colored(
                "You aren't install django-cms. Try to install django-cms<=%s." % SETUP_SUPPORTED_CMS_VERSION, "yellow")
            )
            os.system("pip install \"django-cms<=%s\"" % SETUP_SUPPORTED_CMS_VERSION)
            import cms
            
        cmsVersion = cms.__version__
        
        # check package version
        if django.VERSION <= (2, 0): 
            try:
                os.system(
                    "pip install -U djangocms_text_ckeditor==3.8.0 --no-deps")
                os.system(
                    "pip install -U html5lib==1.0.1 --no-deps")
                os.system("pip install cmsplugin-filer==1.1.3")
            except Exception as e:
                logger.error(
                    colored("Can't install djangocms_text_ckeditor==3.8.0", 
                            "red"))
                sys.exit(1)
        else:
            try:
                os.system(
                    "pip install -U djangocms_text_ckeditor==3.10.0 --no-deps")
            except Exception as e:
                logger.error(
                    colored("Can't install djangocms_text_ckeditor==3.10.0", 
                            "red"))
                sys.exit(1)
            
        sendLog({
            "level": "INFO",
            "message": "User setup template",
            "djangoVersion": djangoVersion,
            "cmsVersion": str(cmsVersion),
            "python": str(sys.version_info),
            "upc": upc,
            "command": cmd,
        })
        
        path = args.path
        
        settingsPath = findSettings(path)
        
        createProject = False
        
        if not settingsPath:
            if not projectName:
                if sys.version_info.major == 3:
                    print()
                    projectName = input(
                        ("Django project not found. "
                         "Auto create one by djangocms-installer==%s."
                         "\nPlease input a project name:") % installVersion)
                else:
                    print
                    projectName = raw_input(
                        ("Django project not found. "
                         "Auto create one by djangocms-installer==%s."
                         "\nPlease input a project name:") % installVersion)
            
            result = os.system(
                "pip install djangocms-installer==%s" % installVersion)
                
            if schemaPath:
                # modify django schema.py
                logger.warning(colored(
                    "There is a django issue (ticket: 29182) which is "
                    "schema corruption issue on SQLite 3.26+. We are trying "
                    "to fix this issue for you to patch your code..."
                    "(You can see https://github.com/django/django/pull"
                    "/10733/commits/c8ffdbe514b55ff5c9a2b8cb8bbdf2d3978c188f"
                    " for more details)", "yellow"))
                fixSchema(schemaPath)
            
            if result != 0:
                logger.error(colored(
                    "Unable to run pip, please check your pip configuration, "
                    "maybe it is because you didn't set python in system PATH "
                    "or broken network connection.", "red"))
                sys.exit(1)
           
            path = os.path.join(path, projectName)
           
            if wizard:
                command = "djangocms -f -p \"%s\" \"%s\" -w" % (
                    path, projectName)
            else:
                command = "djangocms -f -p \"%s\" \"%s\"" % (
                    path, projectName)
                    
            if local and local.upper() in ["ZH_TW", "ZH_HANT"]:
                command = "%s --languages=zh-hant" % command
                
            if djangoVersion:
                command = "%s --django-version=%s" % (
                    command, ".".join(djangoVersion.split(".")[:2]))
                
            if cmsVersion:
                command = "%s --cms-version=%s" % (
                    command, ".".join(cmsVersion.split(".")[:2]))
                
            logger.info(colored(command, "yellow"))
            result = os.system(command)
           
            createProject = True
               
            if not result == 0:
                print("")
                logger.error(colored(
                    "Please check your environment "
                    "which djangocms-installer is installed or "
                    "upgrade to the latest.", "red"))
                sys.exit(1)
               
            settingsPath = findSettings(path)
        else:
            path = os.path.dirname(os.path.dirname(settingsPath))
        
        if not path:
            settingModule = os.path.splitext(settingsPath)[0]
        else:
            settingModule = os.path.splitext(settingsPath[len(path) + 1:])[0]
        settingModule = settingModule.replace("/", ".")
        settingModule = settingModule.replace("\\", ".")
        
        sys.path.append(path)
        os.environ['DJANGO_SETTINGS_MODULE'] = settingModule    

        cmsVersion = cms.__version__.split('.')

        import django
        django.setup()
        
        from django.conf import settings
       
        baseDir = settings.BASE_DIR
       
        # check the project is cms installed.
        apps = [
            'cms',
            'menus',
            'sekizai',
            'treebeard',
            'djangocms_text_ckeditor',
            'filer',
            'easy_thumbnails',
        ]
       
        endSetup = False
        for app in apps:
            if not app in settings.INSTALLED_APPS:
                logger.error(
                    colored(
                    "The app doesn't be included in INSTALLED_APPS: %s" % 
                    app, "red"))
                endSetup = True
       
        if endSetup:
            print("")
            logger.error(
                colored("The project does not support django cms. "
                "Please follow the instructions at "
                "http://docs.django-cms.org/en/stable/how_to/install.html", 
                "red"))
            sys.exit(1)
               
        try:
            templateDir = settings.TEMPLATES[0]['DIRS'][0]
        except Exception as e:
            templateDir = None
       
        try:
            staticDir = settings.STATICFILES_DIRS[0]
        except Exception as e:
            staticDir = None
       
        copyToPath(baseDir, templateDir, staticDir, mode)
       
        if hasattr(settings, "CMS_TEMPLATES"):
            hasCmsTemplate = True
        else:
            hasCmsTemplate = False
           
        writeSettings(settingsPath, 
            templateDir, staticDir, hasCmsTemplate, baseDir, cmsVersion,
            wizard=wizard, createProject=createProject)
           
        os.chdir(baseDir)
           
        success = loadData(baseDir, settings.LANGUAGE_CODE)
        
        if schemaPath:
            # revert django schema.py
            revertSchema(schemaPath)
        
        if not success:
            print("")
            logger.error(
                colored("Please check the project's db was migrated.", "red"))
            logger.error(
                colored("If you encounter \"Could not load xxxxx: UNIQUE constraint failed\","
                        " this is because your project already has CMS data.", "red"))
            sendLog({
                "level": "ERROR",
                "error": traceback.format_exc(),
                "exception": "Loaddata Error",
                "djangoVersion": djangoVersion,
                "cmsVersion": str(cmsVersion),
                "python": str(sys.version_info),
                "upc": upc,
                "createProject": str(createProject),
                "command": cmd,
            })
            sys.exit(1)
        else:
            attrs=['bold']
            print("")
            
            logger.info(
                colored(
                    "Get into ", "yellow") +
                colored("\"%s\"" % path, "white", attrs=['bold',]) +
                colored(" directory and type ", "yellow") +
                colored(
                    "\"python manage.py runserver\"", "white", 
                    attrs=['bold',]) +
                colored(" to start your project" , "yellow")
            )
                        
            if createProject:
                logger.info(
                    colored(
                        "Please enter ", "yellow") +
                    colored("http://localhost:8000/?edit", "white",  
                        attrs=['bold',]) +
                    colored(
                        " to show CMS toolbar. Default super user is ", 
                        "yellow") +
                    colored(
                        "'admin' password: 'admin'.", "white", attrs=['bold',])
                )
                
    except Exception as e:
        print("")
        logger.error(colored("ERROR MESSAGE:", "red"))
        sendLog({
            "level": "ERROR",
            "error": traceback.format_exc(),
            "exception": str(e),
            "djangoVersion": djangoVersion,
            "cmsVersion": str(cmsVersion),
            "python": str(sys.version_info),
            "upc": upc,
            "createProject": str(createProject),
            "command": cmd,
        })
        traceback.print_exc()
        print("")
        logger.error(colored(
            "If you encounter \"django.db.utils.OperationalError: "
            "Problem installing fixtures: no such table: cms_page__old\" "
            "or \"sqlite3.OperationalError: no such table: "
            "cms_cmsplugin__old\", something with \"__old\", "
            "this caused by Django's issue. Please see link: ", "red"))
        logger.error(
            colored("https://github.com/django/django/pull/"
            "10733/commits/c8ffdbe514b55ff5c9a2b8cb8bbdf2d3978c188f", "yellow"))
        logger.error(
            colored("to modify your schema.py to fix this problem.", "red"))
        logger.error(colored(
            "If you encounter \"No such file or directory: "
            "/env/python3/lib/pythonx.x/site-packages/Django-x.x.x.dist-info/METADATA\" "
            "Please execute setup.py again.", "red"))
        logger.error(colored(
            "If you encounter error in \"django.setup()\", "
            "Please use current virtual env(django==%s, cms==%s) to check the project can be run. "
            "This error may come from a wrong version of django." % (djangoVersion, ".".join(cmsVersion)), "red"))
        logger.error(colored(
            "If you encounter \"Loaddata Error\", "
            "Please check your database must be empty before load data.", "red"))
        print("")
        logger.warning(colored(
            "Get more instructions for using setup.py from the URL below:", 
            "yellow", attrs=['bold'])
        )
        logger.warning(colored(
            INTRODUCTION_URL, 
            "white", attrs=['bold'])
        )
    try:
        import json
        if os.path.isfile(os.path.join(SETUP_DIR, 'MANIFAST.INFO')):
            with open(os.path.join(SETUP_DIR, 'MANIFAST.INFO')) as f:
                data = json.loads(f.read())
            tid = 'UA-92158820-3'
            cid = data['upc']
            ec = "Product"
            ea = "Setup"
            el = "upc=%s" % data['upc']
            url = ("https://www.google-analytics.com/collect?"
                    "v=1&t=event&tid=%s&cid=%s&ec=%s&ea=%s&el=%s&ev=300" % (
                        tid, cid, ec, ea, el))
            if sys.version_info.major == 3:
                import urllib.request
                result = urllib.request.urlopen(url)
            else:
                import urllib2
                result = urllib2.urlopen(url)
    except Exception as e:
        pass