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


class TimeoutError(Exception):
    pass

def handler(signum, frame):
    print("Forever is over!")
    raise TimeoutError()
    
TestPassed= True
CurrTestPassed= True


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
         
        
    def start_cmd(self,cmd,stdout=subprocess.PIPE):
        process=subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        encoding='utf8'
        )
        print(cmd)
        stdout = process.communicate()[0]
        print('{}'.format(stdout))
        return
        
    def start_rd_wr(self,cmd):
        return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        encoding='utf8'
        )
    
    def write(self,process, message):
        process.stdin.write(f"{message.strip()}\n")
        process.stdin.flush()
        
    def read_output(self,pipein, qin):
        while True:
            l = pipein.readline()
            qin.put(l)
              
    def setEnvBat(self,source_set):
        fw = open("setenvout", "w+")
        fr = open("setenvout", "r")
        process=subprocess.Popen(source_set,shell=True,stdout=fw,stderr=subprocess.STDOUT,encoding='utf8',universal_newlines=True)
        output = process.communicate()
        SetEnvPattern = re.compile("(\w+)(?:=)(.*)$", re.MULTILINE)
        SetEnvText = fr.read()
        SetEnvMatchList = re.findall(SetEnvPattern, SetEnvText)
        
        for SetEnvMatch in SetEnvMatchList:
            VarName=SetEnvMatch[0]
            VarValue=SetEnvMatch[1]
            os.environ[VarName]=VarValue
            
    def my_callback(self,filename, bytes_so_far, bytes_total):
        print("Transfer of %r is at %d/%d bytes (%.1f%%)" % (filename, bytes_so_far, bytes_total, 100. * bytes_so_far / bytes_total))
        
    def checkIfProcessRunning(self,processName):
        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if processName.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False;

    def l1app_run(self):
        global ip_addr,user_id 
        print("l1app_run")
        self.CommonSetup()
        log_file_path = self.exec_path
        print('**************************')
        text_files = open(self.exec_path + '/' + 'host_details.txt', "w+")
        host_details = 'Target Flexran server' + '    :'+ ip_addr + '  ' + '\nuser id' +'                             :' +  user_id + '  ' + '\nlog file Path ' +'                   :' + '/at/k/Nightly_build' + '  '
        text_files.write(host_details)
        text_files.close()
        self.start_cmd('ls')
        self.start_cmd('pwd')
        os.chdir(self.exec_path)
        self.start_cmd('pwd')
        self.start_cmd('ls')
        subprocess.run(['bash','-c', 'source set_env_var.sh -d  '])
        source_set = '. ./set_env_var.sh -d  '
        self.setEnvBat(source_set)
        os.chdir("bin/nr5g/gnb/l1")
        self.start_cmd('pwd')
        l1app_stdout_file = open(self.exec_path + '/' +'l1appLog.txt', "w+")
        if self.test_mode=='TIMER':
            process = self.start_rd_wr(['stdbuf', '-o0','sh', './l1.sh','-e'])
        elif self.test_mode=='ASFH':
            process = self.start_rd_wr(['stdbuf', '-o0','sh', './l1.sh','-asfh10g'])
        elif self.test_mode=='XRAN':
            process = self.start_rd_wr(['stdbuf', '-o0','sh', './l1.sh','-xran10g'])
        pa_q = queue.Queue()
        pa_t = threading.Thread(target=self.read_output, args=(process.stdout, pa_q))
        pa_t.daemon = True
        pa_t.start()
        while True:
            process.poll()
            if process.returncode is not None :
                break
            try:
                l = pa_q.get(False)
                sys.stdout.write("L1APP: ")
                sys.stdout.write(l)
                l1app_stdout_file .write(l)
            except queue.Empty:
                pass
        l1app_stdout_file.close()
        self.exec_target.close_connection()
        
    def testmac_run(self):
        global test_case_app
        print("testmac_run")
        self.CommonSetup()
        src_path = self.exec_path + '/release_builder/test_case.txt'
        print('src_path')
        print(src_path)
        dest_path = self.exec_path + '/bin/nr5g/gnb/testmac/test_case.txt'
        print('dest_path')
        print(dest_path)
        shutil.copy2(src_path,dest_path)
        testmac_stdout_file = open(self.exec_path + '/' +'testmacLog.txt', "w+")
        testmac_report_stdout_file = open(self.exec_path + '/' +'test_report_Log.txt', "a+")
        self.start_cmd('ls')
        self.start_cmd('pwd')
        os.chdir(self.exec_path)
        self.start_cmd('pwd')
        self.start_cmd('ls')
        subprocess.run(['bash','-c', 'source set_env_var.sh -d  '])
        source_set = '. ./set_env_var.sh -d  '
        self.setEnvBat(source_set)
        os.chdir("bin/nr5g/gnb/testmac")
        self.start_cmd('pwd')
        print("./l2.sh")
        content_array = []
        with open("test_case.txt") as f:
                for line_dat in f:
                    line= str(line_dat)
                    line = line.strip('\n')
                    line = line.strip('\r')
                    content_array.append(line)
                len_cont_arr_asfh = len(content_array)
                print(content_array)
                print(len(content_array))
        if self.checkIfProcessRunning("l1app_main"):
            print("l1app_main was running")
            process = self.start_rd_wr(['stdbuf', '-o0','sh', './l2.sh'])
            if self.test_mode=='ASFH' or self.test_mode=='XRAN':
                self.write(process, self.phy_start)
            self.test_case = content_array[0]
            self.write(process, self.test_case)
            test_case_app = self.test_case
            with open('test_case.txt') as old, open('test_case_testmac.txt', 'w') as new:
                lines = old.readlines()
                new.writelines(lines[1:])
            os.remove("test_case.txt")
            os.rename('test_case_testmac.txt','test_case.txt')
            pb_q = queue.Queue()
            pb_t = threading.Thread(target=self.read_output, args=(process.stdout, pb_q))
            pb_t.daemon = True
            pb_t.start()
            while True:
                process.poll()
                if process.returncode is not None :
                    break
                try:
                    l = pb_q.get(False)
                    sys.stdout.write("TESTMAC: ")
                    sys.stdout.write(l)
                    testmac_stdout_file.write(l)
                    if 'All Tests Completed' in l:
                        sys.stdout.write('**********TESTMAC TEST RESULT STATUS*********' + l)
                        tstpass = re.findall('\d+', l)
                        if tstpass[0] == tstpass[1]:
                            sys.stdout.write("FLEX PASSED\n")
                        else:
                            sys.stdout.write("FLEX FAILED\n")
                        testmac_report_stdout_file.write('\n' + ' ' + self.test_mode +' Testmac tests: ' + self.test_case +' '+ l)
                        testmac_report_stdout_file.close()
                        sys.stdout.write('TESTMAC Testcases executed successfully, I am killing the l1app and testmac process\n' )
                        proc_tmac_main = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
                        output, error = proc_tmac_main.communicate()
                        target_process = "tmac_main"
                        for line in output.splitlines():
                            if target_process in str(line):
                                pid = int(line.split(None, 1)[0])
                                os.kill(pid, 9)
                        proc_l1app_main = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
                        output, error = proc_l1app_main.communicate()
                        target_process = "l1app_main"
                        for line in output.splitlines():
                            if target_process in str(line):
                                pid = int(line.split(None, 1)[0])
                                os.kill(pid, 9)
                        print('*********************************************************************************************************************************************************************')
                        print('***************************************************************************KILLING l1app and testmac***************************************************************')
                        print('*********************************************************************************************************************************************************************')
                        print(Style.RESET_ALL)
                except queue.Empty:
                    pass
            testmac_stdout_file.close()
            self.exec_target.close_connection()
        else:
            print("l1app_main console not getting up")
            with open('test_case.txt') as old, open('test_case_testmac.txt', 'w') as new:
                lines = old.readlines()
                new.writelines(lines[1:])
            self.test_case = content_array[0]
            test_case_app = self.test_case
            os.remove("test_case.txt")
            os.rename('test_case_testmac.txt','test_case.txt')
            testmac_report_stdout_file.write('\n' + ' ' + self.test_mode +' Testmac tests: ' + self.test_case +' '+ 'Timeout Session failed moving to the next test case \n')
            testmac_report_stdout_file.close()
            proc_testmac = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
            output, error = proc_testmac.communicate()
            target_process = "testmac"
            for line in output.splitlines():
                if target_process in str(line):
                    pid = int(line.split(None, 1)[0])
                    os.kill(pid, 9)
            proc_l1app = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
            output, error = proc_l1app.communicate()
            target_process = "l1app"
            for line in output.splitlines():
                if target_process in str(line):
                    pid = int(line.split(None, 1)[0])
                    os.kill(pid, 9)
            print("Process killed")
            self.exec_target.close_connection()
        
    def emsim_run(self):
        print("emsim_run")
        self.CommonSetup()
        src_path = self.exec_path + '/release_builder/test_case.txt'
        print('src_path')
        print(src_path)
        dest_path = self.exec_path_emsim + '/bin/test_case.txt'
        print('dest_path')
        print(dest_path)
        shutil.copy2(src_path,dest_path)
        emsim_stdout_file   = open(self.exec_path_emsim + '/' + 'emsimLog.txt', "w+")
        emsim_report_stdout_file   = open(self.exec_path_emsim + '/' + 'test_report_Log.txt', "w+")
        self.start_cmd('ls')
        self.start_cmd('pwd')
        os.chdir(self.exec_path_emsim)
        self.start_cmd('pwd')
        self.start_cmd('ls')
        os.chdir("bin")
        self.start_cmd('pwd')
        self.start_cmd('ls')
        print("./macsim.sh")
        content_array = []
        with open("test_case.txt") as f:
                for line_dat in f:
                    line= str(line_dat)
                    line = line.strip('\n')
                    line = line.strip('\r')
                    content_array.append(line)
                len_cont_arr_asfh = len(content_array)
                print(content_array)
                print(len(content_array))
        if self.checkIfProcessRunning("l1app_main"):
            print("l1app_main was running")
            process = self.start_rd_wr(['stdbuf', '-o0','sh', './macsim.sh'])
            self.test_case = content_array[0]
            self.write(process, self.test_case)
            test_case_app = self.test_case
            with open('test_case.txt') as old, open('test_case_macsim.txt', 'w') as new:
                lines = old.readlines()
                new.writelines(lines[1:])
            os.remove("test_case.txt")
            os.rename('test_case_macsim.txt','test_case.txt')
            pc_q = queue.Queue()
            pc_t = threading.Thread(target=self.read_output, args=(process.stdout, pc_q))
            pc_t.daemon = True
            pc_t.start()
            while True:
                process.poll()
                if process.returncode is not None :
                    break
                try:
                    l = pc_q.get(False)
                    sys.stdout.write("EMSIM: ")
                    sys.stdout.write(l)
                    emsim_stdout_file.write(l)
                    if 'test cases Finished' in l:
                        sys.stdout.write('**********EMSIM TEST RESULT STATUS*********' + l)
                        tstpass = re.findall('\d+', l)
                        if tstpass[0] == tstpass[1]:
                            sys.stdout.write("FLEX PASSED\n")
                        else:
                            sys.stdout.write("FLEX FAILED\n")
                        emsim_report_stdout_file.write(l)
                        emsim_report_stdout_file.close()
                        sys.stdout.write('EMSIM Testcases executed successfully, I am killing the l1app and testmac process\n' )
                        proc_macsim_main = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
                        output, error = proc_macsim_main.communicate()
                        target_process = "macsim"
                        for line in output.splitlines():
                            if target_process in str(line):
                                pid = int(line.split(None, 1)[0])
                                os.kill(pid, 9)
                        proc_l1app_main = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
                        output, error = proc_l1app_main.communicate()
                        target_process = "l1app_main"
                        for line in output.splitlines():
                            if target_process in str(line):
                                pid = int(line.split(None, 1)[0])
                                os.kill(pid, 9)
                        print('*********************************************************************************************************************************************************************')
                        print('***************************************************************************KILLING l1app and macsim***************************************************************')
                        print('*********************************************************************************************************************************************************************')
                        print(Style.RESET_ALL)
                except queue.Empty:
                    pass
            emsim_stdout_file.close()
            self.exec_target.close_connection()
        else:
            print("l1app_main console not getting up")
            with open('test_case.txt') as old, open('test_case_macsim.txt', 'w') as new:
                lines = old.readlines()
                new.writelines(lines[1:])
            self.test_case = content_array[0]
            test_case_app = self.test_case
            os.remove("test_case.txt")
            os.rename('test_case_macsim.txt','test_case.txt')
            emsim_report_stdout_file.write('\n' + ' ' + self.test_mode +' Emsim tests: ' + self.test_case +' '+ 'Timeout Session failed moving to the next test case \n')
            emsim_report_stdout_file.close()
            proc_emsim = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
            output, error = proc_emsim.communicate()
            target_process = "macsim"
            for line in output.splitlines():
                if target_process in str(line):
                    pid = int(line.split(None, 1)[0])
                    os.kill(pid, 9)
            proc_l1app = subprocess.Popen(['ps', '-a'], stdout=subprocess.PIPE)
            output, error = proc_l1app.communicate()
            target_process = "l1app"
            for line in output.splitlines():
                if target_process in str(line):
                    pid = int(line.split(None, 1)[0])
                    os.kill(pid, 9)
            print("Process killed")
            self.exec_target.close_connection()
      
            
    def testmac_task(self):
        # creating threads 
        global test_case_app
        print("entering testmac_task")
        t1 = threading.Thread(target=self.l1app_run) 
        t2 = threading.Thread(target=self.testmac_run) 
        
        # start threads 
        t1.start() 
        time.sleep(180)
        t2.start() 
        
        # wait until threads finish their job 
        t1.join() 
        t2.join() 
        
        datetime_object = datetime.now()
        dt_string = datetime_object.strftime("_%d_%m_%Y_%H_%M_%S_")
        test_case_app_str = test_case_app.replace(" ", "_")
        self.exec_target.run_cmd('cd /at/k/Nightly_build')
        self.exec_target.run_cmd('mkdir -p Nightly_build'+dt_string+test_case_app_str)
        self.exec_target.run_cmd('cd ' +self.exec_path)
        self.exec_target.run_cmd('cp l1appLog.txt /at/k/Nightly_build/Nightly_build'+dt_string+test_case_app_str)
        self.exec_target.run_cmd('cp testmacLog.txt /at/k/Nightly_build/Nightly_build'+dt_string+test_case_app_str)
        print("testmac_task Done!") 
        
                
    def macsim_task(self):
        # creating threads 
        print("entering macsim_task")
        t1 = threading.Thread(target=self.l1app_run) 
        t2 = threading.Thread(target=self.emsim_run) 
        
        # start threads 
        t1.start() 
        time.sleep(180)
        t2.start() 
        
        # wait until threads finish their job 
        t1.join() 
        t2.join() 
        print("macsim_task Done!") 
             
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
            if session_name=='RUN_TESTMAC_ASFH':
                sess_name=session_name
                sess_ctr +=1
            elif session_name=='RUN_TESTMAC_XRAN':
                sess_name=session_name
                sess_ctr +=1
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
        
        print(child.text +': ' + "executed successfully")
               
                                    
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
