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
from gevent.libev.corecext import child
from nose.plugins import attrib
from conda.common._logic import FALSE
from Cython.Compiler.Naming import self_cname
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
    print_log("Forever is over!")
    raise TimeoutError()

def print_log(log_str=""):
    thread_id= threading.get_ident()
    timestamp= str(time.time())
    out_str= timestamp + "\t" + str(thread_id)+"\t" + log_str  
    print(out_str)
      
TestPassed= True
def check_result(test_res, success_pattern= '[Tt]ests [Pp]assed'):
    global TestPassed
    CurrTestPassed= False
    str_= '\n'.join(test_res)
    perror = re.compile('[Ee]rror')
    m_err= perror.search(str_)
    if m_err:
        CurrTestPassed = False
    else:
        p = re.compile(success_pattern)
        m= p.search(str_)
        if m:
            CurrTestPassed= True
    return CurrTestPassed

def error_chk_flex(test_res, success_pattern= 'FLEX PASSED'):
    CurrTestPassed= False
    str_= '\n'.join(test_res)
    perror = re.compile('FLEX FAILED')
    m_err= perror.search(str_)
    if m_err:
        CurrTestPassed = False
    else:
        p = re.compile(success_pattern)
        m= p.search(str_)
        if m:
            CurrTestPassed= True
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
    #    self.obj = MainHandler()
        self.timeout_err = True
        
    def add_parent_class_callback(self, main_handler):
        self.obj= main_handler

    def get_scp(self, src_file, downloadLocation, recursive=True):
    
        # Where are we putting this?  Make the folder if it doesn't already exist
        print_log('scp_get -r ' + src_file + ' ' + downloadLocation + ' recursive='+str(recursive))
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
            print_log("download error: " + str(e))
            return False 

    def put_scp(self, src_file, dest, recursive=True):
        print_log('scp_put -r ' + src_file + ' ' + dest + ' recursive='+str(recursive))
        scp = SCPClient(self.ssh_client.get_transport())
        for f_name in os.listdir(src_file):
            file_path = src_file+'/'+f_name
            dest_path_file= dest+'/'+f_name
            print_log('copy '+file_path +' to '+ dest_path_file)
            try:
                scp.put(file_path, dest_path_file, recursive)
                
            except scp.SCPException as e:
                print_log("upload error: " + str(e))
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
        print_log("cmd_str="+cmd_str)
        err_check= False
        pass_pattern = None
        if 'chk' in xml_cmd.keys():
            err_check   = True 
        if 'pass' in xml_cmd.keys():
            pass_pattern= xml_cmd.get('pass')
        
        return self.run_cmd(cmd_str, err_check, pass_pattern)
        
    def run_cmd(self, cmd, check_error=False, pass_pattern= None):
        CurrTestPassed = True
        print_log(cmd)
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
                    #print_log(line)
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
                    print_log(line)
                    shout.append(line)
        except TimeoutError  as exc: 
                print_log(exc)
                self.stdin.write('\x03')
                self.stdin.flush()
                # stderr is combined with stdout.
                # thus, swap sherr with shout in a case of failure.
                CurrTestPassed = False
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
            print_log('Error:')
            for err_str in sherr:
                print_log(err_str)
            if check_error==True:
                raise Exception(sherr)
         
        if pass_pattern != None:
            if check_result(shout, pass_pattern)== False:
                CurrTestPassed= False
                
        if CurrTestPassed == True:
            shout.append('Passed')
        else:
            shout.append('Failed')
        return shout 
        
        
    def open_connect(self, main_handler):
        global ip_addr,user_id 
        self.main_handler= main_handler
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.timeout_err = False
        try:
            self.ssh_client.connect(self.ip, port=self.port, username=self.uid, password=self.passw, timeout= float(main_handler.timeout))
            print_log( "Connected successfully. ip =" + self.ip + " user =" + self.uid+" Password = " + self.passw)
            ip_addr = self.ip;
            user_id = self.uid;
            
            
        #except paramiko.AuthenticationException, error:
        except:
            print_log ("Incorrect password: "+self.passw)
            raise
        # except socket.error, error:
        #     print_log(error)
        #    raise
        channel = self.ssh_client.invoke_shell()
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')

        self.is_connected = True
        for cmd in self.prolog:
            res = self.XMLcmd2cmd(cmd)
            #print_log('\n'.join(res))
        

        return 
    
    def close_connection(self):
        try:
            for cmd in self.epilog:
                res = self.XMLcmd2cmd(cmd)
    
            self.is_connected = False
            self.ssh_client.close()
        except:
            print_log( "Warning: disconnect was failed")
        
        
#General class, processing all build, deployment and test requests 
class MainHandler:
    def __init__(self,exec_target):
        #Dictionary of all targets
        self.targets_dict= {}
        #Reference to current target
        self.exec_target = exec_target
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
        self.exec_path_git_repo = '.'
        self.exec_path_release_file = '.'
        self.thread_name = '.'
        self.test_case = '.'
        self.timeout = 300
        self.cmd_list= []
        self.test_name = ''
        self.test_release=''
        self.tests_path = ''
        self.rel_dir = '/tmp/release'
        self.test_case = '.'
        #Add access to environment variables
        self.exec_target.add_parent_class_callback(self)
       
       
        
    def git_local_rep(self):
        global git_clone_rep,git_loc_branch,git_commit_id,git_loc_branch_flex
        self.CommonSetup()
        rem_chars = ["'", "[]"]
        cmd= 'cd '+self.exec_path_git_repo
        self.exec_target.run_cmd(cmd)
        print_log("git_clone_rep")
        git_clone_rep  = self.exec_target.run_cmd('git config --get remote.origin.url')
        git_clone_rep = ''.join(i for i in git_clone_rep if not i in rem_chars)
        print_log("git_loc_branch")
        git_loc_branch = self.exec_target.run_cmd('git symbolic-ref --short HEAD')
        git_loc_branch = ''.join(i for i in git_loc_branch if not i in rem_chars)
        cmd= 'cd '+self.exec_path
        self.exec_target.run_cmd(cmd)
        git_loc_branch_flex = self.exec_target.run_cmd('git symbolic-ref --short HEAD')
        git_loc_branch_flex = ''.join(i for i in git_loc_branch_flex if not i in rem_chars)
        print_log(git_loc_branch_flex)
        print_log("git_commit_id")
        git_commit_id  = self.exec_target.run_cmd('git rev-parse HEAD')
        git_commit_id = ''.join(i for i in git_commit_id if not i in rem_chars)
        datetime_object = datetime.now()
        x_str = datetime_object
        print_log(x_str)
        text_file = open("branch_details.txt", "wt")
        branch_details = ' ******************************* ' + '\n  NIGHTLY BUILD TEST REPORT  '+'\n ******************************* '+'\nTest_ID             '+'               :' +'Nightly_' +str(x_str) +'\nFlexran branch' +'               :' + git_loc_branch_flex + '  \n' + 'Commit id'+'                       :' + git_commit_id + ' \n'
        text_file.write(branch_details)
        text_file.close()  
        self.exec_target.close_connection()
        return True
       
          
    def TargetConfig(self):
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
            self.exec_path_git_repo = self.host_path_git_repo
        
        
    def CommonSetup(self):
        print_log("self.host_switch="+self.host_switch)
        self.TargetConfig()
        self.exec_target.open_connect(self)
        return
         
        
    def start_cmd(self,cmd,stdout=subprocess.PIPE):
        process=subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        encoding='utf8'
        )
        print_log(cmd)
        stdout = process.communicate()[0]
        print_log('{}'.format(stdout))
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
        print_log("Transfer of %r is at %d/%d bytes (%.1f%%)" % (filename, bytes_so_far, bytes_total, 100. * bytes_so_far / bytes_total))
       
        
                
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
        return True
    
    def ping_alive_test(self):
        response= 1
        pingstatus = False
        time.sleep(40)
        tic = time.perf_counter()
        self.TargetConfig()
        for i in range(120):
            response = os.system("ping -c 1 " + self.exec_target.ip)
            # and then check the response...        
            if response == 0:
                print_log("Server alive")
                pingstatus = True
                break
            
            time.sleep(10)
            
        return pingstatus
        
    def reboot_test(self):
        print_log("Test the server reboot")
        self.CommonSetup()
        self.exec_target.run_cmd('reboot &')

        return self.ping_alive_test()
            
        
    def  exec_cmdlist(self):
        print_log("Run commands by list")        
        self.CommonSetup()
        for cmd in self.cmd_list:
            self.exec_target.XMLcmd2cmd(cmd)
        self.exec_target.close_connection()
        return True   
        

#Thread wrapper
class ThreadWrapper(Thread):
    def __init__(self, child, test_handler, attrib, xml_handler):
        threading.Thread.__init__(self)
        self.child= child
        self.test_handler= test_handler
        self.attrib= attrib
        self.xml_handler= xml_handler
        self.result= FALSE
        
    def run(self):
        print_log("Start new thread")
        if self.child.tag == 'thread_session':            
            self.result= self.xml_handler.ActionProcess(self.xml_handler, self.child, self.test_handler, self.attrib)
        elif self.child.tag == 'thread_session':
            self.result= self.xml_handler.SessionProcess(self.xml_handler, self.child.text, self.test_handler, self.attrib)
        else:
            print_log("Error: Wromg tag self.child.tag")
            return False
        
    def join(self):
        Thread.join(self)
        return self.result
                
#Defines general parser class
class XML_handler:
    def __init__(self, test_handler):
        #self.targets_dict= {}
        self.actions_dict= {}
        self.tree= []
        self.file_name = ''
        self.file_nameb= '.'
        self.root = []
        self.test_handler = test_handler
        self.session_dict = {}
        self.iterations=1
        self.threads= []
        
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
                print_log('Error: Target '+ target.get('name') + ' is allocated already')
                raise
            exec_target=  copy.deepcopy(self.test_handler.exec_target)
            for var_name  in target.keys():
                if var_name in exec_target.__dict__.keys():
                    exec_target.__dict__[var_name] = target.get(var_name)
                else:
                    print_log('Warning: Var name '+ var_name + ' is not existed in tatget exec object')
            for child in target:
                if child.tag == 'prolog':
                    for cmd in child:
                        if cmd.tag != 'cmd':
                            print_log('Wrong element in target start prolog: '+ child.tag)
                            raise
                        exec_target.prolog.append(cmd)
                elif child.tag == 'epilog':
                    for cmd in child:
                        if cmd.tag != 'cmd':
                            print_log('Wrong element in target start prolog: '+ child.tag)
                            raise
                        exec_target.epilog.append(cmd)    
                else:
                    print_log('Wrong not cmd element name:'+ cmd.tag)
            #check IP address or convert the server name to IP
            # exec_target.ip= socket.gethostbyname(exec_target.ip)
            #exec_target.ip = socket.gethostbyname(exec_target.name)
            exec_target.name = socket.gethostbyname("")
            self.test_handler.targets_dict[target.get('name')]= copy.deepcopy(exec_target)
            

            
    def AddActions(self, action_root):
        actions_dict =  action_root.find('actions_list')
        if actions_dict == None:
            return
        for action in actions_dict.iter('action'):
            if action.get('name') in actions_dict.keys():
                print_log('Error: Action '+ action.get('name')+ ' is existed already')
                raise
            self.actions_dict[action.get('name')] = action
     
    
    #Processing sessions 
    def SessoinParse(self, session_root):
        session_list=  session_root.find('sessions_list')
        for session in session_list.findall('session'):
            session_name= session.get('name')
            if session_name in self.session_dict.keys():
                print_log('Error: Session ' + session_name + ' already allocated' )
                raise
            print_log("session name " + session_name)
            self.session_dict[session_name] = session
                
    def SessionProcessList(self, session_name_list, main_handler, attrib_dict):
        for session_name in session_name_list:
            print_log('Processing test:'+session_name)
            self.SessionProcess(session_name,main_handler, attrib_dict)   

    def CheckAttribVal(self, key, val):
        mode = ['debug', 'release']
        architecture= ['INTEL', 'ARM']
        if key=='mode' and val not in mode:
            print_log('Config Error: compilation mode is '+ val)
            raise

        if key=='architecture' and val not in architecture:
            print_log('Config Error: architecture is '+ val)
            raise
        #Do not forward the iteration attribute recursively.
        if key == 'iteration':
            return False
        return True
        
        
    def  ActionProcess(self,child, main_handler_orig, child_attrib_dict_tmp):
        global test_report_action
        print_log('Action name='+ child.text)
        action= self.actions_dict[child.text]
        main_handler=  copy.deepcopy(main_handler_orig )
        test_report_action = child.text
        CurrTestPassed = True
        if action == None:
            print_log('Action: '+ child.text + ' did not found in actions list')
            raise
        for attrib in action.keys():
            #Check if the attribute is existed in the main_handler
            if attrib not in main_handler.__dict__:
                print_log('Warning: unused attribute: '+attrib)
            self.CheckAttribVal(attrib, action.get(attrib))
            main_handler.__dict__[attrib] = action.get(attrib)
        #Overwrite Action element attributes if necessary.
        for attrib in child_attrib_dict_tmp.keys():
            #Check if the attribute is existed in the main_handler
            if attrib not in main_handler.__dict__:
                print_log('Warning: unused attribute: '+attrib)
           
            self.CheckAttribVal(attrib, child_attrib_dict_tmp[attrib])
            main_handler.__dict__[attrib] = child_attrib_dict_tmp[attrib]
        
        try:
            func = action.get('func')
            main_handler.test_name= child.get('name')
            func_call = getattr(main_handler, func)
        except AttributeError:
            print_log('Error function name '+ func)

        main_handler.cmd_list= []
        for cmd in action:
            if cmd.tag != 'cmd':
                print_log('Wrong cmd list tag '+ cmd.tag)
                raise
            main_handler.cmd_list.append(cmd)
        CurrTestPassed= func_call()
        #Check if test_descr attribute  is existed. If this attribute is existed then the test results should be saved
        test_res= "Failed"
        if CurrTestPassed == True:
            test_res= "Passed"

        print_log(child.text +': ' + test_res)
     #   if hasattr(main_handler, "test_descr"):
     #       result_file.write(main_handler.test_descr+ ': ' + test_res + '\n')
     #       result_file.flush()
        return CurrTestPassed
        
        
                                    
    def     SessionProcess(self, session_name, main_handler_orig, attrib_dict= {}):    
        TestPassed = True
        print_log()                     
        print_log('Execute session ' + session_name)
        print_log('Attrib_dict: '+ str(attrib_dict.keys()))
        main_handler=  copy.deepcopy(main_handler_orig )
        session= self.session_dict.get(session_name)
        if session == None:
            print_log('Unallocated session name ' + session_name)
            raise
        child_attrib_dict= dict(attrib_dict)  
        #Go through attributes and set them in the main_handler
        for attrib in session.keys():
            #Check if the attribute is existed in the main_handler
            if attrib not in child_attrib_dict.keys():
                child_attrib_dict[attrib] = session.get(attrib)
            else: 
                #Check if the local attributes are more important than external.              
                if self.CheckAttribVal(attrib, child_attrib_dict[attrib])== True:
                    child_attrib_dict[attrib] = session.get(attrib)
                
        TotalTestRes = True     
        #Run the tests
        for iter_num in range(int(self.iterations)):
            for child in session:
                #Add attributes if they were not added before
                child_attrib_dict_tmp = dict(child_attrib_dict)
                child_attrib_dict_tmp['iter_num']= str(iter_num)
                for attrib in child.keys():
                    if attrib not in child_attrib_dict_tmp.keys():
                        child_attrib_dict_tmp[attrib] = child.get(attrib)
                   
                if child.tag == 'session':
                    TestPassed = self.SessionProcess(child.text, main_handler, child_attrib_dict_tmp)
                elif child.tag == 'action':
                    TestPassed = self.ActionProcess(child, main_handler, child_attrib_dict_tmp)
                elif child.tag == 'thread_session' or child.tag == 'thread_action':
                    new_thread= ThreadWrapper(self, child, main_handler, child_attrib_dict_tmp)
                    self.threads.append(new_thread)
                    new_thread.start()
                
                else:
                    print_log('Wrong session element parameter '+ child.tag)
                    raise
                
                TotalTestRes = TotalTestRes and TestPassed
            for t in self.threads:
                TestPassed= t.join()
                TotalTestRes = TotalTestRes and TestPassed
            
        print_log('Finish executing session ' + session_name )
                    
        if TotalTestRes== True:
            print_log('Automation test passed')
            return True
        else:
            print_log('Automation test failed')
            return False
    
    def DataParserList(self, files_list):
        for file in files_list:
            print_log('Parsing XML file:'+ file)
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
def test_processing(xml_handler):
    parser = argparse.ArgumentParser(usage="python3 test_drive.py --config [config1.xml config1.xml..] --tst [list of test session names] --rel_dir release_directory")
    parser.add_argument('--config', required=True, nargs="*", help="List of test onfiguration files")
    parser.add_argument('--tst', required=True, nargs="*", help="Names of session from XML files to run")
    parser.add_argument('--rel_dir', default="/tmp/release", help="Path to the release directory")
    parser.add_argument('--email', nargs="*", type=str, help="List of emails to send result")
    
    x = sys.argv
    del x[0]
    attrib= {}
    args = parser.parse_args(x)
    xml_handler.DataParserList(args.config)
    attrib['rel_dir'] = args.rel_dir
    rel_dir_path  = args.rel_dir
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
            print_log(pwd_path)
            rel_dir_up = rel_dir_path + '/test_report_Log.txt'
            rel_dir_path_host_details = rel_dir_path + '/host_details.txt'
            print_log(pwd_path)
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
            src_addr= 'automation-support@ethernitynet,com'
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

#exec_target= ExecTarget() #Select class, supporting low level communication with target
#test_handler = MainHandler(exec_target) #Select class, implementing tests actions
#xml_handler= XML_handler(test_handler) #select class, implementing tests grouping
#test_processing(xml_handler)

