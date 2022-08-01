# Script for running system tests
# Running options:
# python3 <path>/test.py [path to tests] [nameof test]
# Examples:
# - Running tests from default folder ../Tests/DU/GLUE_LOGIC_TEST/Test_Vec/Test1
# python3 ../Tests/DU/GLUE_LOGIC_TEST/test.py 
#  Running tests from explicit directory   ../Tests/DU/GLUE_LOGIC_TEST/Test_Vec/Test2
# python3 ../Tests/DU/GLUE_LOGIC_TEST/test.py --tst ../Tests/DU/GLUE_LOGIC_TEST/Test_Vec/Test2
#  Running test2_2 from ../Tests/DU/GLUE_LOGIC_TEST/Test_Vec/Test2 directory
# python3  ../Tests/DU/GLUE_LOGIC_TEST/test.py --tst ../Tests/DU/GLUE_LOGIC_TEST/Test_Vec/Test2 test2_2
import os
import sys
print(sys.version)
import time
import re
#import rpyc
#import numpy as np
#import matplotlib.pyplot as plt
import paramiko
print (paramiko.__version__)
from scp import SCPClient, SCPException
#import pandas as pd
import xml.etree.ElementTree as ET
import socket
import copy
import pathlib
import subprocess
from threading import Thread
from queue import Queue
import tempfile
import select
from subprocess import Popen, PIPE, DEVNULL
import threading 
import functools
import signal
from colorama import Fore, Back, Style 
import inspect
import queue
import shlex
import shutil
from datetime import datetime
import psutil
# from keyboard import press

#from _ast import Raise

# from sphinx.util.pycompat import sys_encoding
# time.sleep(30)
class TimeoutError(Exception):
    pass

def handler(signum, frame):
    print("Forever is over!")
    raise TimeoutError()
    
TestPassed= True
CurrTestPassed= True
def check_result(test_res, success_pattern= '[Tt]ests [Pp]assed'):
    global TestPassed, CurrTestPassed
    CurrTestPassed= False
    str= '\n'.join(test_res)
    perror = re.compile('[Ee]rror')
    m_err= perror.search(str)
    if m_err:
        CurrTestPassed = False
    else:
        p = re.compile(success_pattern)
        m= p.search(str)
        if m:
            CurrTestPassed= True
    TestPassed = TestPassed and CurrTestPassed
    return CurrTestPassed

def error_chk_flex(test_res, success_pattern= 'FLEX PASSED'):
    global TestPassed, CurrTestPassed
    CurrTestPassed= False
    str= '\n'.join(test_res)
    perror = re.compile('FLEX FAILED')
    m_err= perror.search(str)
    if m_err:
        CurrTestPassed = False
    else:
        p = re.compile(success_pattern)
        m= p.search(str)
        if m:
            CurrTestPassed= True
    TestPassed = TestPassed and CurrTestPassed
    return CurrTestPassed
        
        

class ExecTarget:
    def __init__(self):
        self.ip = '0.0.0.0'
        self.prolog = []
        self.epilog = []
        self.port = 22
        self.is_connected = False
        self.name = 'LocalTarget'
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.uid = 'swuser'
        self.passw= 'sw_grp2'
        self.obj = MainHandler()
        self.timeout_err = True
        


    def get_scp(self, src_file, downloadLocation, recursive=True):
    
        # Where are we putting this?  Make the folder if it doesn't already exist
        print('scp_get -r ' + src_file + ' ' + downloadLocation + ' recursive='+str(recursive))
        if not os.path.exists(downloadLocation):
            try:
                os.makedirs(downloadLocation)
            except FileExistsError:
                pass
        # SCPCLient takes a paramiko transport as an argument
        scp = SCPClient(self.ssh_client.get_transport())
        try:
            scp.get(src_file, downloadLocation, recursive)
            scp.close()
            return True
        except scp.SCPException as e:
            print("download error: " + str(e))
            return False 

    def put_scp(self, src_file, dest, recursive=True):
        print('scp_put -r ' + src_file + ' ' + dest + ' recursive='+str(recursive))
        scp = SCPClient(self.ssh_client.get_transport())
        for f_name in os.listdir(src_file):
            file_path = src_file+'/'+f_name
            dest_path_file= dest+'/'+f_name
            print('copy '+file_path +' to '+ dest_path_file)
            try:
                scp.put(file_path, dest_path_file, recursive)
                
            except scp.SCPException as e:
                print("upload error: " + str(e))
                scp.close()
                return False
        scp.close()
        return True 
   
    def XMLcmd2cmd(self, xml_cmd):
        obj= self.main_handler
        if 'record_name' in xml_cmd.keys():
            obj.test_descr= eval(xml_cmd.text)
            return
        
        cmd_str= eval(xml_cmd.text)
        err_check= False
        pass_pattern = None
        if 'chk' in xml_cmd.keys():
            err_check   = True 
        if 'pass' in xml_cmd.keys():
            pass_pattern= xml_cmd.get('pass')
        
        return self.run_cmd(cmd_str, err_check, pass_pattern)
        
    def run_cmd(self, cmd, check_error=False, pass_pattern= None):
        print(cmd)
        if self.timeout_err == True:
            return
        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        start_str= 'end of stdOUT buffer'
        finish = start_str+'. finished with exit status'
        
        echo_cmd = 'echo {} $?'.format(finish)
        self.stdin.write(echo_cmd + '\n')
        #shin = self.stdin
        self.stdin.flush()
        p_cmd = re.compile(cmd)
        p_echo= re.compile('(echo)\s*'+start_str)
        shout = []
        sherr = []
        exit_status = 0
        timeout_sec= int(self.main_handler.timeout)
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout_sec)
        try:
            for line_dat in self.stdout:
                line= str(line_dat)
                line = line.strip('\n')
                line = line.strip('\r')
                if p_cmd.search(line):
                    #print(line)
                    # up for now filled with shell junk from stdin
                    shout = []
                elif p_echo.search(line):
                    pass
                elif line.startswith(finish):
                    # our finish command ends with the exit status
                    exit_status = int(line.rsplit(maxsplit=1)[1])
                    if exit_status and check_error==True:
                        # stderr is combined with stdout.
                        # thus, swap sherr with shout in a case of failure.
                        sherr = shout
                        shout = []
                    break
                else:
                    # get rid of 'coloring and formatting' special characters
                    print(line)
                    shout.append(line)
        except TimeoutError  as exc: 
                print(exc)
                self.stdin.write('\x03')
                self.stdin.flush()
                # stderr is combined with stdout.
                # thus, swap sherr with shout in a case of failure.
                global TestPassed , CurrTestPassed
                CurrTestPassed = False
                TestPassed = CurrTestPassed
                sherr = shout
                self.timeout_err = True
                shout = []
        finally:
            signal.alarm(0)

        # first and last lines of shout/sherr contain a prompt
        if shout and echo_cmd in shout[-1]:
            shout.pop()
        if shout and cmd in shout[0]:
            shout.pop(0)
        if sherr and echo_cmd in sherr[-1]:
            sherr.pop()
        if sherr and cmd in sherr[0]:
            sherr.pop(0)

        
        if len(sherr)!= 0:
            print('Error:')
            for err_str in sherr:
                print(err_str)
            if check_error==True:
                raise Exception(sherr)
         
        if pass_pattern != None:
            if check_result(shout, pass_pattern)== False:
                shout.append('Command failed')
        return shout 
        
        
    def open_connect(self, main_handler):
        global ip_addr,user_id 
        self.main_handler= main_handler
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.timeout_err = False
        try:
            self.ssh_client.connect(self.ip, port=self.port, username=self.uid, password=self.passw, timeout= float(main_handler.timeout))
            print( "Connected successfully. ip =" + self.ip + " user =" + self.uid+" Password = " + self.passw)
            ip_addr = self.ip;
            user_id = self.uid;
            
            
        #except paramiko.AuthenticationException, error:
        except:
            print ("Incorrect password: "+self.passw)
            raise
        # except socket.error, error:
        #     print(error)
        #    raise
        channel = self.ssh_client.invoke_shell()
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')

        self.is_connected = True
        for cmd in self.prolog:
            res = self.XMLcmd2cmd(cmd)
            #print('\n'.join(res))
        

        return 
    
    def close_connection(self):
        for cmd in self.epilog:
            res = self.XMLcmd2cmd(cmd)

        self.is_connected = False
        self.ssh_client.close()
        
#General class, processing all build, deployment and test requests 
class MainHandler:
    def __init__(self):
        #Dictionary of all targets
        self.targets_dict= {}
        #Reference to current target
        self.exec_target = None
        self.host_switch= 'False'
        self.target = ''
        self.host =''
        self.host_path= '.'
        self.host_path_emsim= '.'
        self.host_path_phy5g= '.'
        self.host_path_git_repo = '.'
        self.architecture='INTEL'
        self.mode = 'release'
        self.exec_path = '.'
        self.exec_path_emsim = '.'
        self.exec_path_Flexran = '.'
        self.exec_path_phy5g = '.'
        self.exec_path_git_repo = '.'
        self.exec_path_artifacts_dir = '.'
        self.exec_path_release_file = '.'
        self.thread_name = '.'
        self.test_case = '.'
        self.timeout = 300
        self.cmd_list= []
        self.test_name = ''
        self.test_release=''
        self.tests_path = ''
        self.ant_mode='_4x4_'
        self.rel_dir = '/tmp/PHY_RELEASE'
        self.rt_mode='_RU_OFFLINE_'
        self.test_case = '.'
       
        
    def git_local_rep(self):
        global git_clone_rep,git_loc_branch,git_commit_id,git_loc_branch_flex
        self.CommonSetup()
        rem_chars = ["'", "[]"]
        cmd= 'cd '+self.exec_path_git_repo
        self.exec_target.run_cmd(cmd)
        print("git_clone_rep")
        git_clone_rep  = self.exec_target.run_cmd('git config --get remote.origin.url')
        git_clone_rep = ''.join(i for i in git_clone_rep if not i in rem_chars)
        print("git_loc_branch")
        git_loc_branch = self.exec_target.run_cmd('git symbolic-ref --short HEAD')
        git_loc_branch = ''.join(i for i in git_loc_branch if not i in rem_chars)
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        git_loc_branch_flex = self.exec_target.run_cmd('git symbolic-ref --short HEAD')
        git_loc_branch_flex = ''.join(i for i in git_loc_branch_flex if not i in rem_chars)
        print(git_loc_branch_flex)
        print("git_commit_id")
        git_commit_id  = self.exec_target.run_cmd('git rev-parse HEAD')
        git_commit_id = ''.join(i for i in git_commit_id if not i in rem_chars)
        datetime_object = datetime.now()
        x_str = datetime_object
        print(x_str)
        text_file = open("branch_details.txt", "wt")
        branch_details = ' ******************************* ' + '\n  NIGHTLY BUILD TEST REPORT  '+'\n ******************************* '+'\nTest_ID             '+'               :' +'Nightly_' +str(x_str) +'\nFlexran branch' +'               :' + git_loc_branch_flex + '  \n' + 'Commit id'+'                       :' + git_commit_id + ' \n'
        text_file.write(branch_details)
        text_file.close()  
        self.exec_target.close_connection()
       
          
    def git_remote_rep(self):
        global git_clone_rep,git_loc_branch,git_commit_id,git_loc_branch_flex
        self.CommonSetup()
        rem_chars = ["'", "[]"]
        print(git_clone_rep)
        self.exec_target.run_cmd('mkdir -p '+self.exec_path_git_repo)
        self.exec_target.run_cmd('cd '+self.exec_path_git_repo)
        ls_dir = self.exec_target.run_cmd('ls')
        ls_dir = ''.join(i for i in ls_dir if not i in rem_chars)
        if 'PHY5G_Rel' in ls_dir:
            self.exec_target.run_cmd('cd PHY5G_Rel/' )
        else:
            self.exec_target.run_cmd('git clone --recurse-submodules ssh://git@bitbucket-il:7999/phy-5g/phy5g_rel.git PHY5G_Rel')
            cmd_ckout_new = 'git checkout'+ ' '+ '-b' +' ' + git_loc_branch
            self.exec_target.run_cmd(cmd_ckout_new)
            self.exec_target.run_cmd('cd PHY5G_Rel/' )
                
        git_remote_rep = self.exec_target.run_cmd('git config --get remote.origin.url')
        git_remote_rep = ''.join(i for i in git_remote_rep if not i in rem_chars)
        if 'ssh://git@bitbucket-il:7999/phy-5g/phy5g_rel.git' in git_remote_rep:
            print('git_remote_rep exists')
        else:
            self.exec_target.run_cmd('cd ../ ')
            self.exec_target.run_cmd('rm -rf PHY5G_Rel/ ')
            print("do git cloning for phy5g_rel.git PHY5G_Rel")
            self.exec_target.run_cmd('git clone --recurse-submodules ssh://git@bitbucket-il:7999/phy-5g/phy5g_rel.git PHY5G_Rel')
            cmd_ckout_new = 'git checkout'+ ' '+ '-b' +' ' + git_loc_branch
            self.exec_target.run_cmd(cmd_ckout_new)
        git_branch_all = self.exec_target.run_cmd('git branch')
        str= '\n'.join(git_branch_all)
        p = re.compile(git_loc_branch)
        m= p.search(str)
        if m:
            cmd_ckout = 'git checkout'+ ' '+ git_loc_branch
        else : 
            cmd_ckout = 'git checkout'+ ' '+ '-b' + ' ' + git_loc_branch
        self.exec_target.run_cmd(cmd_ckout)
        self.exec_target.run_cmd('git fetch && git pull')
        cmd_commit_id = 'git reset --hard' + ' ' + git_commit_id
        self.exec_target.run_cmd(cmd_commit_id)
        self.exec_target.run_cmd('pwd')
        self.exec_target.run_cmd('ls')
        cmd= 'cd '+ self.exec_path_git_repo + '/PHY5G_Rel/FlexRanPHY/FlexRan/' 
        self.exec_target.run_cmd(cmd)
        cmd_ckout_flex = 'git checkout'+ ' '+ git_loc_branch_flex
        self.exec_target.run_cmd(cmd_ckout_flex)
        self.exec_target.run_cmd('git fetch && git pull')
        self.exec_target.run_cmd('pwd')
        self.exec_target.run_cmd('ls')
        self.exec_target.run_cmd('yes | cp -r sdk '  + self.exec_path)
        self.exec_target.run_cmd('yes | cp -r tests ' + self.exec_path)
        self.exec_target.close_connection()

        
    def CommonSetup(self):
        print("self.host_switch="+self.host_switch)
        if self.host_switch== 'False' or self.host == '':
            self.exec_target  = self.targets_dict[self.target]
            if self.host != '':
                self.exec_host= self.targets_dict[self.host]
        else:
            #The treatment case, when executables and tests are located on host server and target 
            #is mounted to the host server. In that case the host_switch allows running automatic
            #data deployment on host and running tests on target
            self.exec_target  = self.targets_dict[self.host]
            if self.target!= '':
                self.exec_host= self.targets_dict[self.target]
            self.exec_path = self.host_path
            self.exec_path_emsim = self.host_path_emsim
            self.exec_path_phy5g = self.host_path_phy5g
            self.exec_path_git_repo = self.host_path_git_repo
        self.exec_target.open_connect(self)
        return
        
    def ru_build(self):
        print("Build RU")
        self.CommonSetup()
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('mkdir -p '+self.rel_dir)
        if self.architecture=='INTEL':
            self.exec_target.run_cmd('source setup_ru_x86.sh')
            self.exec_target.run_cmd('cp setup_ru_x86.sh ' + self.rel_dir)
        else:
            self.exec_target.run_cmd('source setup_ru_nxp.sh')
            self.exec_target.run_cmd('cp setup_ru_nxp.sh ' + self.rel_dir)
            
        build_dir = self.exec_target.run_cmd('pwd')[0] + '/bin'
        #cmd= 'make clean architecture='+self.architecture + ' BIN='+build_dir
        self.exec_target.run_cmd(cmd)
        cmd= 'make clean architecture='+self.architecture +' BIN='+build_dir
        self.exec_target.run_cmd(cmd)
        cmd= 'make ru mode=' + self.mode + ' architecture='+self.architecture + ' ant_mode='+self.ant_mode+' rt_mode='+self.rt_mode +' BIN='+build_dir
        self.exec_target.run_cmd(cmd, True)
    
        rel_name = 'ru_phy_'+self.architecture+'_'+self.mode+'_'+self.ant_mode +'_'+self.rt_mode+'.tgz '
        self.exec_target.run_cmd('tar -czf '+ rel_name + ' bin')
        self.exec_target.run_cmd('mkdir -p '+self.rel_dir)
        self.exec_target.run_cmd('cp ' + rel_name + ' ' + self.rel_dir, True)
        self.test_descr= 'RU Build ' + self.ant_mode + ' ' + self.architecture+ ' ' + self.rt_mode + ' ' +self.mode
        self.exec_target.close_connection()
        
    def l1_build(self):
        print("Build L1app")
        self.CommonSetup()
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('export WIRELESS_SDK_STANDARD=5gnr')
        self.exec_target.run_cmd('export WIRELESS_SDK_TARGET_ISA=avx512')
        self.exec_target.run_cmd('export CMAKE_BUILD_TYPE=Release')
        self.exec_target.run_cmd('source set_env_var.sh -d --as-phy '+self.exec_path_phy5g)
        self.exec_target.run_cmd('cd sdk/')
        self.exec_target.run_cmd('ls')
        self.exec_target.run_cmd('./create-makefiles-linux.sh ')
        self.exec_target.run_cmd('cd build-avx512-icc/ ')
        self.exec_target.run_cmd('make && make install')
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('cd source/test/EMSIM')
        self.exec_target.run_cmd('make BIN=' +self.exec_path_emsim +'/src/macsim/lib')
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('./flexran_build.sh -e -r 5gnr_sub6 -b -m all')
        self.exec_target.close_connection()
        
    def l1_build_pack(self):
        self.CommonSetup()
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.run_cmd('pwd',True)
        self.exec_target.run_cmd('mkdir -p '+self.rel_dir)
        self.exec_target.run_cmd('cd '+self.rel_dir)
        self.exec_target.run_cmd('rm -fr *')
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('cp flexran_build.sh ' + self.rel_dir)
        self.exec_target.run_cmd('cp set_env_var.sh ' + self.rel_dir)
        self.exec_target.run_cmd('tar -cvzf' + ' ' +'l1app' +'.tgz'+ ' ' + 'bin'+ ' ' + 'tests'+ ' ' + 'sdk'+ ' ' + 'libs' + ' ' + 'wls_mod')
        self.exec_target.run_cmd('cp l1app.tgz' +' ' + self.rel_dir)
        self.exec_target.run_cmd('cd ' + self.rel_dir, True)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.close_connection()
        
    def l1_HIPHY_rel(self):
        self.CommonSetup()
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.run_cmd('pwd',True)
        self.exec_target.run_cmd('mkdir -p '+self.rel_dir)
        self.exec_target.run_cmd('cd '+self.rel_dir)
        self.exec_target.run_cmd('rm -fr *')
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('cp -R' + ' ' + 'bin'+ ' ' + 'libs' + ' ' + 'wls_mod'+' ' + self.rel_dir)
        self.exec_target.run_cmd('cd ' + self.rel_dir, True)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.run_cmd('mkdir -p emsim_plug ')
        self.exec_target.run_cmd('cd  emsim_plug/')
        self.exec_target.run_cmd('mkdir -p api')
        self.exec_target.run_cmd('mkdir -p lib')
        self.exec_target.run_cmd('cp' + ' ' +self.exec_path+ '/source/test/EMSIM/emsim_pluggin_api.h' +' ' + self.rel_dir + '/emsim_plug/api')
        self.exec_target.run_cmd('cp' + ' ' +self.exec_path_emsim + '/src/macsim/lib/EMSIM.so' +' ' + self.rel_dir + '/emsim_plug/lib')
        self.exec_target.run_cmd('cd' + ' ' + self.rel_dir, True)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.run_cmd('mkdir -p fapi_api')
        self.exec_target.run_cmd('cd fapi_api/')
        self.exec_target.run_cmd('mkdir -p source')
        self.exec_target.run_cmd('cd source/')
        self.exec_target.run_cmd('mkdir -p common')
        self.exec_target.run_cmd('cp' + ' ' + self.exec_path + '/source/common/common_typedef.h'+' '+ self.rel_dir + '/fapi_api/source/common')
        self.exec_target.run_cmd('cp' + ' ' +self.exec_path+'/source/common/phy_version.h' + ' ' + self.rel_dir + '/fapi_api/source/common')
        self.exec_target.run_cmd('cd' + ' ' + self.rel_dir + '/fapi_api/source')
        self.exec_target.run_cmd('mkdir -p nr5g')
        self.exec_target.run_cmd('cd nr5g')
        self.exec_target.run_cmd('mkdir -p api')
        self.exec_target.run_cmd('cp' + ' ' + self.exec_path + '/source/nr5g/api/gnb_l1_l2_api.h'+' '+ self.rel_dir + '/fapi_api/source/nr5g/api')
        self.exec_target.run_cmd('cd' + ' ' + self.rel_dir +'/libs')
        self.exec_target.run_cmd('rm -rf flx_rt_debug roe mlog wiresharkL1 ferrybridge')
        self.exec_target.run_cmd('ls')
        self.exec_target.run_cmd('cd' +' ' +'../')
        self.exec_target.run_cmd('cd' +' ' +'wls_mod')
        self.exec_target.run_cmd('rm -rf BSDLicense postclean syslib.h versionfile wls_lib.h build.sh LICENSE.GPL _postinstall syslib.o  filelist Makefile README testapp   wls_lib_dpdk.c  _postbuild syslib.c ttypes.h wls_lib_dpdk.o')
        self.exec_target.run_cmd('mkdir -p api')
        self.exec_target.run_cmd('cp' + ' ' + self.rel_dir +'/wls_mod/wls.h' + ' ' + self.rel_dir + '/wls_mod/api')
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('ls ')
        self.exec_target.run_cmd('cp -R' + ' ' +self.exec_path+'/sdk' + ' ' + self.rel_dir )
        self.exec_target.run_cmd('cd ' + self.rel_dir + '/sdk')
        self.exec_target.run_cmd('rm -rf create-makefiles-linux.sh source cmake Intel_Wireless_Software_Clickwrap_License.txt test CMakeLists.txt kernel-list-icc.cmake ')
        self.exec_target.run_cmd('cp -R' + ' ' +self.exec_path+'/set_env_var.sh' + ' ' + self.rel_dir )
        self.exec_target.run_cmd('cd ' + self.rel_dir)
        self.exec_target.run_cmd('mkdir -p Dependancy')
        self.exec_target.run_cmd('cd ' + 'bin/') 
        self.exec_target.run_cmd('rm -rf lte ')
        self.exec_target.run_cmd('cd '+self.rel_dir+'/libs/cpa')
        self.exec_target.run_cmd('rm -rf mmw')
        self.exec_target.run_cmd('cd '+self.rel_dir)
        self.exec_target.run_cmd('tar -cvzf' + ' ' +'L1_Release' +'.tgz'+ ' ' + 'bin'+ ' ' + 'emsim_plug'+ ' ' + 'set_env_var.sh'+ ' ' + 'Dependancy' + ' ' + 'fapi_api'+ ' ' +'libs'+ ' ' + 'wls_mod'+ ' ' + 'sdk')
        self.exec_target.run_cmd('yes | cp L1_Release.tgz' +' ' + self.exec_path_release_file)
        self.exec_target.run_cmd('cd '+self.exec_path)
        self.exec_target.run_cmd('cd ../../')
        self.exec_target.run_cmd('pwd')
        self.exec_target.run_cmd('ls')
        print("Building Docker")
        self.exec_target.run_cmd('cd Docker/ ')
        self.exec_target.run_cmd('./make_docker.sh -a '+self.exec_path_artifacts_dir+ ' '+'-r' + ' '+self.exec_path_release_file+'/L1_Release.tgz'+' '+ '-o' +' '+ self.rel_dir +' ' +'-d' )
        self.exec_target.close_connection()
        
    def emsim_build(self):
        print("Build EMSIM")
        self.CommonSetup()
        cmd= 'cd '+self.exec_path_emsim
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('pwd',True)
        self.exec_target.run_cmd('mkdir -p '+self.rel_dir)
        self.exec_target.run_cmd('cd'+ ' ' +self.rel_dir)
        self.exec_target.run_cmd('rm -fr *')
        self.exec_target.run_cmd('cd ' + self.exec_path)
        self.exec_target.run_cmd('cd ' + self.exec_path)
        self.exec_target.run_cmd('source set_env_var.sh -d --as-phy '+self.exec_path_phy5g)
        self.exec_target.run_cmd('cd'+ ' ' +self.exec_path_emsim +'/src/macsim/src/wls_mod ',True)
        self.exec_target.run_cmd('./build.sh dpdk_wls')
        self.exec_target.run_cmd('cd'+ ' ' +self.exec_path_emsim +'/src/macsim/build ' ,True)
        self.exec_target.run_cmd('make clean')
        self.exec_target.run_cmd('make WLS_DPDK=YES')
        self.exec_target.run_cmd('cd'+ ' ' +self.exec_path_emsim +'/src/macsim ' ,True)
        self.exec_target.run_cmd('ls ',True)
        self.exec_target.run_cmd('tar -cvzf' + ' ' +'emsim_bin' +'.tgz'+ ' ' + 'bin'+ ' ' + 'test'+ ' ' + 'lib'+ ' ' + 'config')
        self.exec_target.run_cmd('ls ',True)
        self.exec_target.run_cmd('cp emsim_bin.tgz' +' ' + self.rel_dir)
        self.exec_target.run_cmd('cd'+ ' ' +self.exec_path_phy5g +'/Tests/RU ' ,True)
        self.exec_target.run_cmd('tar -cvzf' + ' ' +'fpga_proto' +'.tgz'+ ' ' + 'FPGA_PROTO')
        self.exec_target.run_cmd('cp fpga_proto.tgz' +' ' + self.rel_dir)
        self.exec_target.close_connection()
        
    def ru_phy_test_prepare(self):
    #Copy tests to git repository
        print('ru_phy_test_prepare')
        self.CommonSetup()
        self.exec_target.run_cmd('pwd')
        cmd = 'cp -rf '+ self.tests_path+ '/test_2_layers_2ant' + ' Tests/RU/BUILD_ORAN_PACKETS/Test_Vec/Test1'
        self.exec_target.run_cmd(cmd)
        cmd = 'cp -rf '+ self.tests_path+ '/test_4_layers_4ant' + ' Tests/RU/BUILD_ORAN_PACKETS/Test_Vec/Test2'
        self.exec_target.run_cmd(cmd)
        cmd = 'cp -rf '+ self.tests_path+ '/test_8_layers_32ant' + ' Tests/RU/BUILD_ORAN_PACKETS/Test_Vec/Test3'    
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('tar -czf Tests.tgz Tests')
        self.exec_target.run_cmd('cp Tests.tgz ' + self.rel_dir, True)
        self.exec_target.close_connection()
        
    def ru_phy_deploy(self):    
        print('ru_phy_test_deploy')
        self.CommonSetup()
        self.exec_target.run_cmd('mkdir -p '+self.exec_path)
        self.exec_target.run_cmd('cd ' + self.exec_path, True)
        self.exec_target.run_cmd('rm -fr *')
        cur_path= self.exec_target.run_cmd('pwd')[0]
        self.exec_target.run_cmd('ls '+ self.rel_dir)
        sftp = self.exec_target.ssh_client.open_sftp()
        # Get file list       
        fn_list = sftp.listdir(self.rel_dir)
        for file in fn_list:
            self.exec_target.run_cmd('cp -f '+ self.rel_dir+'/'+file + ' '+cur_path+'/'+file)
        #self.exec_target.put_scp(self.rel_dir, cur_path)
        self.exec_target.run_cmd('tar -xf Tests.tgz ')
        self.exec_target.run_cmd('chmod -R 777 *')
        self.exec_target.close_connection()
        
    def l1_phy_deploy(self):    
        print('l1_phy_test_deploy')
        self.CommonSetup()
        self.exec_target.run_cmd('mkdir -p '+self.exec_path)
        self.exec_target.run_cmd('cd ' + self.exec_path, True)
        self.exec_target.run_cmd('rm -fr *')
        cur_path= self.exec_target.run_cmd('pwd')[0]
        print('*********************************************************************************************************************************************************************')
        print("**********************Deploying release files from VM to Flexran server*******************************")
        print('*********************************************************************************************************************************************************************')
        sftp = self.exec_target.ssh_client.open_sftp()
        for filename in sorted(os.listdir(self.rel_dir)):
            callback_for_filename = functools.partial(self.my_callback, self.rel_dir+'/'+filename)
            sftp.put(self.rel_dir+'/'+filename,cur_path+'/'+filename,callback=callback_for_filename)
        self.exec_target.run_cmd('tar -xvzf l1app.tgz ')
        self.exec_target.run_cmd('pwd')
        self.exec_target.run_cmd('ls')
        self.exec_target.run_cmd('chmod -R 777 *')
        self.exec_target.close_connection()

    def l1_re_build(self):
        print('l1_re_build')
        self.CommonSetup()
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.run_cmd('source set_env_var.sh -d')
        self.exec_target.run_cmd('./flexran_build.sh -e -r 5gnr_sub6 -m all -b')
        self.exec_target.close_connection()


    def l1_build_mini_pack(self):    
        print('l1_mini_pack')
        self.CommonSetup()
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.run_cmd('tar -cvzf' + ' ' +'l1app_mini' +'.tgz'+ ' ' + 'l1'+ ' ' + 'testmac'+ ' ')
        self.exec_target.run_cmd('cd '+self.rel_dir)
        self.exec_target.run_cmd('rm -fr l1app_mini.tgz')
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('cp l1app_mini.tgz' +' ' + self.rel_dir)
        self.exec_target.close_connection() 

    def l1_mini_deploy(self):    
        print('l1_mini_deploy')
        self.CommonSetup()
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        self.exec_target.run_cmd('rm -fr l1app_mini.tgz')
        self.exec_target.run_cmd('rm -fr l1 testmac')
        sftp = self.exec_target.ssh_client.open_sftp()
        cur_path= self.exec_target.run_cmd('pwd')[0]
        print('*********************************************************************************************************************************************************************')
        print("**********************Deploying L1 and TESTMAC from VM to Flexran server*******************************")
        print('*********************************************************************************************************************************************************************')
        for filename in sorted(os.listdir(self.rel_dir)): 
            if filename == 'l1app_mini.tgz':
                 callback_for_filename = functools.partial(self.my_callback, self.rel_dir+'/'+filename)
                 sftp.put(self.rel_dir+'/'+filename,cur_path+'/'+filename,callback=callback_for_filename)
        self.exec_target.run_cmd('tar -xvzf l1app_mini.tgz ')
        #self.exec_target.run_cmd('ls ', True)
        self.exec_target.close_connection() 

    def emsim_bin_deploy(self):    
        print('emsim_bin_deploy')
        self.CommonSetup()
        self.exec_target.run_cmd('mkdir -p '+self.exec_path)
        self.exec_target.run_cmd('cd ' + self.exec_path, True)
        self.exec_target.run_cmd('rm -fr *')
        cur_path= self.exec_target.run_cmd('pwd')[0]
        print('*********************************************************************************************************************************************************************')
        print("**********************Deploying release files from VM to Flexran server*******************************")
        print('*********************************************************************************************************************************************************************')
        sftp = self.exec_target.ssh_client.open_sftp()
        for filename in sorted(os.listdir(self.rel_dir)):
            callback_for_filename = functools.partial(self.my_callback, self.rel_dir+'/'+filename)
            sftp.put(self.rel_dir+'/'+filename,cur_path+'/'+filename,callback=callback_for_filename)
        self.exec_target.run_cmd('tar -xvzf emsim_bin.tgz ')
        self.exec_target.run_cmd('pwd')
        self.exec_target.run_cmd('ls')
        self.exec_target.run_cmd('chmod -R 777 *')
        self.exec_target.run_cmd('tar -xvzf fpga_proto.tgz ')
        self.exec_target.run_cmd('cd FPGA_PROTO ')
        self.exec_target.run_cmd('chmod -R 777 *')
        self.exec_target.close_connection()
        
    def ru_glue_logic_test(self):
        print("Test RU")
        self.CommonSetup()
        self.exec_target.run_cmd('cd ' + self.exec_path, True)
        self.exec_target.run_cmd('pwd')
        self.exec_target.run_cmd('ls')
        if self.architecture=='INTEL':
            self.exec_target.run_cmd('source setup_ru_x86.sh')
            cmd= '/opt/anaconda3/bin/python3 ' 
        else:
#            self.exec_target.run_cmd('source setup_ru_arm.sh')
            cmd= 'python '
        self.exec_target.run_cmd('export LD_LIBRARY_PATH=.:/$LD_LIBRARY_PATH')
        self.exec_target.run_cmd('cd bin', True)
        if self.ant_mode=='_2x2_':
            tst_path= 'Test1'
        elif self.ant_mode=='_4x4_':
            tst_path= 'Test2'
        elif self.ant_mode=='_8x32_':
            tst_path= 'Test3'
        else:
            raise
        cmd_gl= cmd+ ' ../Tests/RU/GLUE_LOGIC_TEST/test.py --tst ../Tests/RU/GLUE_LOGIC_TEST/Test_Vec/'+tst_path
        cmd_oran= cmd+ ' ../Tests/RU/BUILD_ORAN_PACKETS/test.py --tst ../Tests/RU/BUILD_ORAN_PACKETS/Test_Vec/'+tst_path
        test_res= self.exec_target.run_cmd(cmd_oran)
        check_result(test_res )
        test_res= self.exec_target.run_cmd(cmd_gl)
        check_result( test_res)           
        self.test_descr= 'RU Glue Logic Test ' + self.ant_mode + ' ' + self.architecture + ' '+ self.rt_mode+ ' ' + self.mode
        self.exec_target.close_connection()
    
            
    def my_callback(self,filename, bytes_so_far, bytes_total):
        print("Transfer of %r is at %d/%d bytes (%.1f%%)" % (filename, bytes_so_far, bytes_total, 100. * bytes_so_far / bytes_total))
       
        
    def run_target_prepare(self):
        global rel_dir_path,sess_ctr
        self.CommonSetup()
        self.exec_target.run_cmd('pwd')
        self.exec_target.run_cmd('cd ' + self.rel_dir, True)
        self.exec_target.run_cmd('ls ')
        self.exec_target.run_cmd('pwd ')
        self.exec_target.run_cmd('cd ' +self.exec_path_git_repo)
        self.exec_target.run_cmd('ls ')
        self.exec_target.run_cmd('pwd ')
        self.exec_target.run_cmd('cd release_builder')
        self.exec_target.run_cmd('ls ')
        self.exec_target.run_cmd('pwd ')
        self.exec_target.run_cmd('touch test_case.txt')
        print(self.test_case)
        self.exec_target.run_cmd('cat '+self.test_case+' '+'>'+' ' +'test_case.txt')
        self.exec_target.run_cmd('cd ' +self.exec_path_git_repo)
        self.exec_target.run_cmd('tar -cvzf' + ' ' +'release_builder' +'.tgz'+ ' ' + 'release_builder')
        self.exec_target.run_cmd('ls')
        self.exec_target.run_cmd('yes | cp release_builder.tgz' +' ' + self.rel_dir)
        self.exec_target.run_cmd('cd ' + self.rel_dir, True)
        self.exec_target.run_cmd('ls ', True)
        self.exec_target.run_cmd('pwd ')
        rel_dir_path = self.exec_target.run_cmd('pwd ', True)
        rem_chars = ["'", "[]"]
        rel_dir_path = ''.join(i for i in rel_dir_path if not i in rem_chars)
        self.exec_target.run_cmd('cd ' +self.exec_path_git_repo)
        self.exec_target.run_cmd('cd release_builder')
        self.exec_target.close_connection()
         
    def run_testmac_macsim(self):
        global sess_ctr,sess_name
        self.CommonSetup()
        self.exec_target.run_cmd('cd ' +self.exec_path)
        self.exec_target.run_cmd('rm -rf release_builder* ')
        lp_rb = self.rel_dir + '/' + 'release_builder.tgz'
        print("self.rel_dir")
        print(self.rel_dir)
        print("self.exec_path")
        print(self.exec_path)
        rp_rb = self.exec_path + '/' + 'release_builder.tgz'
        sftp = self.exec_target.ssh_client.open_sftp()
        callback_for_filename = functools.partial(self.my_callback, lp_rb)
        sftp.put(lp_rb,rp_rb,callback=callback_for_filename)
        sftp.put(lp_rb,rp_rb)
        self.exec_target.run_cmd('tar -xvzf release_builder.tgz ')
        self.exec_target.run_cmd('cd release_builder ')
        self.exec_target.run_cmd('ls')
        content_array = []
        with open("test_case.txt") as f:
            for line_dat in f:
                line= str(line_dat)
                line = line.strip('\n')
                line = line.strip('\r')
                content_array.append(line)
        len_cont_arr = len(content_array)
        print(content_array)
        print(len(content_array))
        print(self.configlistToStr)
        res_k = str([self.thread_name] * len_cont_arr)
        rem_chars = ["'", ",", "[]"]
        res_k = ''.join(i for i in res_k if not i in rem_chars)
        l1app_testmac_thrd = str(res_k)[1:-1]
        print(l1app_testmac_thrd)
        flex_emsim_cmd = '/opt/anaconda3/bin/python3 test_threads.py --config ' + self.configlistToStr + ' ' + '--tst ' +l1app_testmac_thrd+ ' '+ '--rel_dir' +' '+self.rel_dir
        self.exec_target.run_cmd('pwd')
        test_res = self.exec_target.run_cmd(flex_emsim_cmd)
        error_chk_flex( test_res)     
        self.exec_target.close_connection()
                
    def test_report_build(self):
        self.CommonSetup()
        self.exec_target.run_cmd('cd ' +self.exec_path)
        lp_rep = self.rel_dir + '/'  + 'test_report_Log.txt'
        rp_rep = self.exec_path + '/' + 'test_report_Log.txt'
        lph_rep = self.rel_dir + '/'  + 'host_details.txt'
        rph_rep = self.exec_path + '/' + 'host_details.txt'
        sftp = self.exec_target.ssh_client.open_sftp()
        sftp.get(rp_rep, lp_rep)
        sftp.get(rph_rep, lph_rep)
        self.exec_target.close_connection()
        
        
    def  exec_cmdlist(self):
        print("Run commands by list")
        self.CommonSetup()
        for cmd in self.cmd_list:
            self.exec_target.XMLcmd2cmd(cmd)
        self.exec_target.close_connection()
        return    
        
        
#Defines general parser class
class XML_handler:
    def __init__(self):
        #self.targets_dict= {}
        self.actions_dict= {}
        self.tree= []
        self.file_name = ''
        self.file_nameb= '.'
        self.root = []
        self.test_handler = MainHandler()
        self.session_dict = {}
        
    def Init(self, file_name):
        self.file_name = file_name
        self.tree = ET.parse(self.file_name)
        self.root = self.tree.getroot()
        
    def AddTargets(self, target_root):
        targets_list= target_root.find('targets_list')
        if targets_list== None:
            return
        for target in targets_list.iter('target'):
            if target.get('name') in self.test_handler.targets_dict.keys():
                print('Error: Target '+ target.get('name') + ' is allocated already')
                raise
            exec_target= ExecTarget()
            for var_name  in target.keys():
                if var_name in exec_target.__dict__.keys():
                    exec_target.__dict__[var_name] = target.get(var_name)
                else:
                    print('Warning: Var name '+ var_name + ' is not existed in tatget exec object')
            for child in target:
                if child.tag == 'prolog':
                    for cmd in child:
                        if cmd.tag != 'cmd':
                            print('Wrong element in target start prolog: '+ child.tag)
                            raise
                        exec_target.prolog.append(cmd)
                elif child.tag == 'epilog':
                     for cmd in child:
                        if cmd.tag != 'cmd':
                            print('Wrong element in target start prolog: '+ child.tag)
                            raise
                        exec_target.epilog.append(cmd)    
                else:
                    print('Wrong not cmd element name:'+ cmd.tag)
            #check IP address or convert the server name to IP
            # exec_target.ip= socket.gethostbyname(exec_target.ip)
            #exec_target.ip = socket.gethostbyname(exec_target.name)
            exec_target.name = socket.gethostbyname("")
            self.test_handler.targets_dict[target.get('name')]= exec_target
            

            
    def AddActions(self, action_root):
        actions_dict =  action_root.find('actions_list')
        if actions_dict == None:
            return
        for action in actions_dict.iter('action'):
            if action.get('name') in actions_dict.keys():
                print('Error: Action '+ action.get('name')+ ' is existed already')
                raise
            self.actions_dict[action.get('name')] = action
     
    
    #Processing sessions 
    def SessoinParse(self, session_root):
        session_list=  session_root.find('sessions_list')
        for session in session_list.findall('session'):
            session_name= session.get('name')
            if session_name in self.session_dict.keys():
                print('Error: Session ' + session_name + ' already allocated' )
                raise
            self.session_dict[session_name] = session
                
    def SessionProcessList(self, session_name_list, main_handler, attrib_dict):
        global sess_ctr,sess_name
        for session_name in session_name_list:
            print('Processing test:'+session_name)
            self.SessionProcess(session_name,main_handler, attrib_dict)   

    def CheckAttribVal(self, key, val):
        ant_mode = ['_2x2_', '_4x4_', '_8x32_']
        mode = ['debug', 'release']
        architecture= ['INTEL', 'ARM']
        if key=='mode' and val not in mode:
            print('Config Error: compilation mode is '+ val)
            raise
        if key=='ant_mode' and val not in ant_mode:
            print('Config Error: MIMO mode is '+ val)
            raise
        if key=='architecture' and val not in architecture:
            print('Config Error: architecture is '+ val)
            raise
        
    def  ActionProcess(self,child, main_handler_orig, child_attrib_dict_tmp):
        global result_file,test_report_action
        print('Action name=', child.text)
        action= self.actions_dict[child.text]
        main_handler=  copy.deepcopy(main_handler_orig )
        test_report_action = child.text

        if action == None:
            print('Action: '+ child.text + ' did not found in actions list')
            raise
        for attrib in action.keys():
            #Check if the attribute is existed in the main_handler
            if attrib not in main_handler.__dict__:
                print('Warning: unused attribute: '+attrib)
            self.CheckAttribVal(attrib, action.get(attrib))
            main_handler.__dict__[attrib] = action.get(attrib)
        #Overwrite Action element attributes if necessary.
        for attrib in child_attrib_dict_tmp.keys():
            #Check if the attribute is existed in the main_handler
            if attrib not in main_handler.__dict__:
                print('Warning: unused attribute: '+attrib)
           
            self.CheckAttribVal(attrib, child_attrib_dict_tmp[attrib])
            main_handler.__dict__[attrib] = child_attrib_dict_tmp[attrib]
        
        try:
            func = action.get('func')
            main_handler.test_name= child.get('name')
            func_call = getattr(main_handler, func)
        except AttributeError:
            print('Error function name '+ func)
        main_handler.cmd_list= []
        for cmd in action:
            if cmd.tag != 'cmd':
                print('Wrong cmd list tag '+ cmd.tag)
                raise
            main_handler.cmd_list.append(cmd)
        func_call()
        #Check if test_descr attribute  is existed. If this attribute is existed then the test results should be saved
        test_res= "Failed"
        if CurrTestPassed == True:
            test_res= "Passed"

        print(child.text +': ' + test_res)
        if hasattr(main_handler, "test_descr"):
            result_file.write(main_handler.test_descr+ ': ' + test_res + '\n')
            result_file.flush()
        return
        
        
                                    
    def     SessionProcess(self, session_name, main_handler_orig, attrib_dict= {}):    
        global TestPassed,sess_ctr,sess_name,len_cont_arr_asfh,len_cont_arr_xran
        print()                     
        print('Execute session ' + session_name)
        print('Attrib_dict: '+ str(attrib_dict.keys()))
        main_handler=  copy.deepcopy(main_handler_orig )
        session= self.session_dict.get(session_name)
        if session == None:
            print('Unallocated session name ' + session_name)
            raise
        child_attrib_dict= dict(attrib_dict)  
        #Go through attributes and set them in the main_handler
        for attrib in session.keys():
            #Check if the attribute is existed in the main_handler
            if attrib not in child_attrib_dict.keys():
                child_attrib_dict[attrib] = session.get(attrib)
                 
        #Run the tests
        for child in session:
            #Add attributes if they were not added before
            child_attrib_dict_tmp = dict(child_attrib_dict)
            for attrib in child.keys():
                if attrib not in child_attrib_dict_tmp.keys():
                    child_attrib_dict_tmp[attrib] = child.get(attrib)
               
            if child.tag == 'session':
                 self.SessionProcess(child.text, main_handler, child_attrib_dict_tmp)
            elif child.tag == 'action':
                self.ActionProcess(child, main_handler, child_attrib_dict_tmp)
            else:
                print('Wrong session element parameter '+ child.tag)
                raise
        print('Finish executing session ' + session_name )
                    
        if TestPassed== True:
            print('Automation test passed')
        else:
            print('Automation test failed')
    
    def DataParserList(self, files_list):
        for file in files_list:
            print('Parsing XML file:'+ file)
            self.DataParser(file)
            
    
    def DataParser(self, file):
        #Get targets
        tree = ET.parse(file)
        root = tree.getroot()
        self.AddTargets(root)
        self.AddActions(root)
        self.SessoinParse(root)        
                        
                
            
    
    

import argparse
#parser = argparse.ArgumentParser(usage="python3 release_builde.py -config [config1.xml config1.xml..] --tst [list of test session names] --rel_dir release_directory")
parser = argparse.ArgumentParser(usage="python3 release_builder.py --config [config1.xml config1.xml..] --tst [list of test session names] --rel_dir release_directory")
parser.add_argument('--config', required=True, nargs="*", help="List of test onfiguration files")
parser.add_argument('--tst', required=True, nargs="*", help="Names of session from XML files to run")
parser.add_argument('--rel_dir', default="/tmp/PHY_RELEASE", help="Path to the release directory")
parser.add_argument('--email', nargs="*", type=str, help="List of emails to send result")

x = sys.argv
del x[0]
attrib= {}
sess_ctr = 0
args = parser.parse_args(x)
xml_handler= XML_handler()
xml_handler.DataParserList(args.config)
attrib['rel_dir'] = args.rel_dir
attrib['configlistToStr']= ' '.join(map(str, args.config)) 
res_file_name= "test_results.txt"
result_file= open(res_file_name, 'w')
session_cntr =0
xml_handler.SessionProcessList(args.tst, xml_handler.test_handler, attrib) 
result_file.close()  
#Email support
if args.email:
    # Import smtplib for the actual sending function
    import smtplib

    # Import the email modules we'll need
    from email.message import EmailMessage
    
    # Open the plain text file whose name is in textfile for reading.
    with open(res_file_name) as fp:
        # Create a text/plain message
        msg = EmailMessage()
        msg.set_content(fp.read())
    if 'test_report_build' in test_report_action:
        pwd_path = os.getcwd()
        print(pwd_path)
        rel_dir_up = rel_dir_path + '/test_report_Log.txt'
        rel_dir_path_host_details = rel_dir_path + '/host_details.txt'
        print(pwd_path)
        shutil.copy2(rel_dir_up,pwd_path)
        shutil.copy2(rel_dir_path_host_details,pwd_path)
        filenames = ["branch_details.txt", "host_details.txt", "test_report_Log.txt"]
        with open("automation_report.txt", "w+") as outfile:
            for filename in filenames:
                with open(filename) as infile:
                    contents = infile.read()
                    outfile.write(contents)
                outfile.write("\n")
        test_report = open('automation_report.txt', 'r')
        lines = test_report.readlines()
        test_report_n_ints = ''
        for i in lines:
            test_report_n_ints = test_report_n_ints + i
        msg.set_content(test_report_n_ints)
    # me == the sender's email address
    # you == the recipient's email address
    src_addr= 'automation-support@airspan,com'
    res_total = 'Failed'
    
    
    if TestPassed== True:
        src_addr= 'automation-support@airspan,com'
        res_total= 'Passed'
    
    dest_addresses = ", ".join(args.email)
    # msg['Subject'] = 'PHY Nightly tests: '+ res_total
    msg['Subject'] = 'PHY Nightly tests summary'
    msg['From'] = src_addr
    msg['To'] = dest_addresses

    
    # Send the message via our own SMTP server.
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    # subject = 'PHY Nightly tests: '+ res_total
    subject = 'PHY Nightly tests summary'
    s.quit()

