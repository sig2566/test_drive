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
from conda.common._logic import FALSE, TRUE
from Cython.Compiler.Naming import self_cname
from networkx.generators import line
from anaconda_project.internal.cli.environment_commands import lock
from spyder.plugins.variableexplorer.widgets.objectexplorer import attribute_model
print(sys.version)
import time
import re
from random import uniform
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
#Attributes, which are not transfered from up to down
attribute_exception_list = ["iterations", "timeout", "name"]

# from sphinx.util.pycompat import sys_encoding
# time.sleep(30)
class TimeoutError(Exception):
    pass

def handler(signum, frame):
    print_log("Forever is over!")
    raise TimeoutError()
lock_print = threading.Lock()
def print_log(log_str=""):
    global lock_print
    lock_print.acquire()
    thread_name= threading.currentThread().getName()
    timestamp= str(time.time())
    out_str= timestamp + "\t" + thread_name+"\t" + log_str  
    print(out_str, end ="\n")
    lock_print.release()
      
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
        self.prolog = []
        self.epilog = []
        self.is_connected = False
        self.name = 'LocalTarget'
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
     #    self.obj = MainHandler()
        self.timeout_err = True
        self.stdin = None 
        self.stdout = None
        self.stderr= None
        self.channel=paramiko.Channel
        self.attrib_dict= {}
        self.attrib_dict['port']= '22'
        self.attrib_dict['ip']= '0.0.0.0'
        self.attrib_dict['uid']='swuser'
        self.attrib_dict['passw']='sw_grp2'
        self.attrib_dict['disabled_algorithms']= ''

        
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
        action_delay= 1 #Default wait for action 1 sec
        cmd_str= eval(xml_cmd.text)
        print_log("cmd_str="+cmd_str)
        err_check= False
        pass_pattern = None
        final_pattern = None
        timeout_action= None
        if 'chk' in xml_cmd.keys():
            err_check   = True 
        if 'pass' in xml_cmd.keys():
            pass_pattern= xml_cmd.get('pass')
            
        
        if 'final' in xml_cmd.keys():
            final_pattern= xml_cmd.get('final')
            
        if 'timeout_action' in xml_cmd.keys():
            timeout_action=xml_cmd.get('timeout_action')
            
        if 'action_delay' in xml_cmd.keys():
            action_delay= int(xml_cmd.get('action_delay'))
            
        
        return self.run_cmd(cmd_str, err_check, pass_pattern, finish_str= final_pattern, timeout_action= timeout_action, action_delay= action_delay)
        
    def run_cmd(self, cmd, check_error=False, pass_pattern= None, finish_str= None, timeout_action = None, action_delay= 1):
        finish_tst_str = None
        CurrTestPassed = True
        immideately_exit = False
        print_log(cmd)
        if self.timeout_err == True:
            return
        cmd = cmd.strip('\n')
          
        action_delay_num = action_delay* 10
        # wait until channel is ready
        # while not self.channel.recv_ready() :
        #     print("NOT READY " + str(self.channel.recv_ready()) + "\n \n")
        #     time.sleep(1)
        if self.channel.closed:
            return
            
        self.channel.send(cmd)
        self.channel.send("\n")
        shout = []
        sherr = []

        # Wait a bit, if necessary
        time.sleep(1)
        start_str= 'end of stdOUT buffer'
        if finish_str != None:
            if finish_str =='.':
                shout.append('Passed')
                return shout
            else:
                finish_mark= re.compile(finish_str)
        else:
             #Added new line to check that the previous command was ended                  
            finish_tst_str = start_str+'. finished with exit status'        
            echo_cmd = 'echo {} $?'.format(finish_tst_str)
            if self.channel.closed:
                return
            self.channel.send(echo_cmd)
            self.channel.send("\n")
       
        
        #Check that the command was started
        p_cmd = re.compile(cmd)
        p_echo= re.compile('(echo)\s*'+start_str)
        exit_status = 0
        timeout_sec= int(self.main_handler.timeout)
        signal.alarm(timeout_sec)
        print_log("timeout_sec=" + str(timeout_sec))
        more_cont_str= "--More--"
        more_re= re.compile(more_cont_str)
        cmd_fnished= False
        last_line= ""
        iter= 0
        try:
            while not  self.channel.closed:
                iter= iter+1
                time.sleep(0.1)
                while self.channel.recv_ready():
                    iter= 0
                    time.sleep(0.1)
                    line_dat = self.channel.recv(5000)
                    line_tmp= line_dat.decode("utf-8")
                    lines = line_tmp.split('\n')
                    num_lines= len(lines)
                    lines[0] = last_line+lines[0]
                    last_line= lines[num_lines-1]
                    for i in range(num_lines):
                        line= lines[i]                        
                        if p_cmd.search(line):
                            #Not treat the line with the command
                            #print_log(line)
                            # up for now filled with shell junk from stdin
                            #print("p_cmd.search(line)")
                            shout = []                     
                        elif immideately_exit:
                            cmd_fnished= True
                            break
                        elif (finish_tst_str!= None) and line.startswith(finish_tst_str):
                            # our finish command ends with the exit status
                            #exit_status = int(line.rsplit(maxsplit=1)[1])
                            #print_log(line)
                            #if exit_status and check_error==True:
                            cmd_fnished= True
                            #print("startswith(finish_tst_str)")
                            break 
                        elif (finish_str != None) and finish_mark.search(line):
                            print_log(line)
                            cmd_fnished= True
                            #print("finish_mark.search(line)")
                            break 
                        elif p_echo.search(line):
                            #print("p_echo.search(line)")
                            pass
                        elif more_re.search(line):
                            self.channel.send(" ")
                            #print("more_re.search(line)")
                        else:
                            # get rid of 'coloring and formatting' special characters
                            print_log(line)
                            shout.append(line)
                if cmd_fnished== True:
                    #print("cmd_fnished== True")
                    break        
                if iter > action_delay_num:
                    if timeout_action != None:
                        if timeout_action == "exit":
                            CurrTestPassed = False
                            self.timeout_err = True                        
                            break
                        else:
                            if timeout_action == "exception":
                                signal.alarm(0)
                            else:
                                if timeout_action == "new_line":
                                    iter=0
                                    self.channel.sendall("\n")
                                else:
                                    break
                    
                
        except TimeoutError  as exc: 
            print_log('TimeoutError')
            self.channel.sendall('\x03')
            
            # stderr is combined with stdout.
            # thus, swap sherr with shout in a case of failure.
            CurrTestPassed = False
            sherr = shout
            self.timeout_err = True
            shout = []
            signal.alarm(0)
        except UnicodeDecodeError as exc:
            print_log("Exit due to input data exception")
            shout.append('Passed')
            return shout
            

        # first and last lines of shout/sherr contain a prompt
        if finish_tst_str!= None:
            if shout and echo_cmd in shout[-1]:
                shout.pop()
            if shout and cmd in shout[0]:
                shout.pop(0)
            if sherr and echo_cmd in sherr[-1]:
                sherr.pop()
            if sherr and cmd in sherr[0]:
                sherr.pop(0)

        
        if self.channel.recv_stderr_ready():
            print_log('Error:')
            
            while self.channel.recv_stderr_ready():
                err_str = self.channel.recv_stderr(1000)
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
        obj= main_handler
        self.main_handler= main_handler
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.timeout_err = False
        try:
            self.ssh_client.connect(obj.ip, port=obj.port, username=obj.uid, password=obj.passw, 
                                    timeout= float(main_handler.timeout), disabled_algorithms = obj.disabled_algorithms)
            print_log( "Connected successfully. ip =" + obj.ip + " user =" + obj.uid+" Password = " + obj.passw)
            ip_addr = obj.ip;
            user_id = obj.uid;
            
            
        #except paramiko.AuthenticationException, error:
        except:
            print_log ("Exeption of ssh connection setup: "+ " UID=" + obj.uid + " PSSW:" + obj.passw + " IP:"+obj.ip+ ' port:'+obj.port)
            raise
        # except socket.error, error:
        #     print_log(error)
        #    raise
        self.channel = self.ssh_client.invoke_shell()
        self.stdin = self.channel.makefile('ab') 
        self.stdout = self.channel.makefile('r')
        self.stderr= self.channel.makefile_stderr()

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
        self.iter_num= 0
        self.start_time=0
        self.end_time=3
        self.setups_dict= {}
        
       
        
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
        
        #Random delay between start_time till end_time.
        #The start_time and end_time may be specified as attributes
    def random_delay(self):
        if int(self.start_time)>= int(self.end_time):
            print_log("Sleep was failed. wrong start and stop times"+ self.start_time+ ' '+ self.end_time)
            return False
        delay_time= uniform(int(self.start_time), int(self.end_time))
        print_log("Delay started for "+ str(delay_time) + ' sec')
        time.sleep(delay_time)
        print_log("Finish delay")
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
        
        for attrib in self.__dict__.keys():
                if attrib in self.exec_target.__dict__.keys():
                    self.exec_target.__dict__[attrib]= self.__dict__.get(attrib)
        
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
            response = os.system("ping -c 1 " + self.ip)
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
            res= self.exec_target.XMLcmd2cmd(cmd)

        self.exec_target.close_connection()
        return True   
        

#Thread wrapper
class ThreadWrapper(Thread):
    def __init__(self, thread_name, child, test_handler, attrib, xml_handler):
        threading.Thread.__init__(self, name= thread_name)
        self.child= copy.deepcopy(child)
        self.test_handler= test_handler
        self.attrib= attrib
        self.xml_handler= xml_handler
        self.result= False
        
    def run(self):
        print_log("Start new thread")
        if self.child.tag == 'thread_session':
            #child, main_handler_orig, child_attrib_dict_tmp    
            self.result= self.xml_handler.SessionProcess(cover_session= self.child, main_handler_orig= self.test_handler, attrib_dict= self.attrib, new_thread= True)
        elif self.child.tag == 'thread_action':
            self.child.tag = "action"
            #session_name, main_handler_orig, attrib_dict
            self.result= self.xml_handler.ActionProcess(child= self.child, main_handler_orig= self.test_handler, child_attrib_dict_tmp=self.attrib)
        else:
            print_log("Error: Wromg tag self.child.tag")
            return False
        
    def join(self):
        Thread.join(self)
        return self.result
                
#Defines general parser class
class XML_handler:
    def __init__(self, test_handler):
        self.targets_dict= {}
        self.actions_dict= {}
        self.setups_dict= {}
        self.tree= []
        self.file_name = ''
        self.file_nameb= '.'
        self.root = []
        self.test_handler = test_handler
        self.session_dict = {}
        self.iterations=1
        self.timeout = 30
        
    def Init(self, file_name):
        self.file_name = file_name
        self.tree = ET.parse(self.file_name)
        self.root = self.tree.getroot()
    
    def AddSetups(self, setups_root):
        setups_list= setups_root.find('setups_list')
        if setups_list== None:
            return
        for setup in setups_list:
            setup_dict= {}
            setup_name= setup.get('name')
            if setup_name == None:
                print_log('Error: Setup name does not exist ' + setup_name)
                raise 
            attrib_list= list(setup.findall('attrib'))
            for child in attrib_list:
                if child.tag != 'attrib':
                    print_log('Wrong element in setup attribute element: '+ child.tag)
                    raise
                
                if 'id' not in child.attrib.keys():
                    print_log('Error: Attrib id is not exist in setup ' + setup_name)
                    raise
                
                if 'new_val' not in child.keys():
                    print_log('Error: Attrib new_val is not exist in setup ' + setup_name)
                    raise 
                
                if 'val' in child.keys():
                    key= child.attrib['id'] + '.' + child.attrib['val']
                else:
                    key= child.attrib['id']
                
                if key in setup_dict.keys():
                    print_log('Error: Attrib was defined already ' + key)
                    raise 
                setup_dict[key] =  child.attrib['new_val']
            if setup_name in self.test_handler.setups_dict.keys():
                print_log('Error: Setup name was defined already ' + setup_name)
                raise 
            self.test_handler.setups_dict[setup_name] = setup_dict
          
    def AddTargets(self, target_root):
        targets_list= target_root.find('targets_list')
        if targets_list== None:
            return
        for target in targets_list.iter('target'):
            if target.get('name') in self.test_handler.targets_dict.keys():
                print_log('Error: Target '+ target.get('name') + ' is allocated already')
                raise
            exec_target=  copy.deepcopy(self.test_handler.exec_target)
            #exec_target.__dict__['attrib_dict']= {}
            for var_name  in target.keys():
                if var_name not in exec_target.attrib_dict.keys():
                    print_log('Warning: Var name '+ var_name + ' is not existed in tatget exec object')
                exec_target.attrib_dict[var_name] = target.get(var_name)
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
        if session_list == None:
            return
        for session in session_list.findall('session'):
            session_name= session.get('name')
            if session_name in self.session_dict.keys():
                print_log('Error: Session ' + session_name + ' already allocated' )
                raise
            print_log("session name " + session_name)
            self.session_dict[session_name] = session
                
    def SessionProcessList(self, session_name_list, main_handler, attrib_dict):
        signal.signal(signal.SIGALRM, handler)
        cover_session = {}
        
        for session_name in session_name_list:
            print_log('Processing test:'+session_name)
            cover_session = ET.Element("session")
            cover_session.text = session_name
            self.SessionProcess(cover_session, main_handler, attrib_dict)   

    def CheckAttrbUpDownOrder(self, key, val):
        mode = ['debug', 'release']
        architecture= ['INTEL', 'ARM']
        if key=='mode' and val not in mode:
            print_log('Config Error: compilation mode is '+ val)
            raise

        if key=='architecture' and val not in architecture:
            print_log('Config Error: architecture is '+ val)
            raise
        #Do not forward the iteration attribute recursively.
        if key in attribute_exception_list:
            return False
        return True
        
    def  AttributeUpdate_with_setup(self, attrib, attrib_dict):
        if 'setup' not in attrib_dict.keys():
            return
        setup_name= attrib_dict['setup']
        if setup_name == None:
            return
        if self.test_handler.setups_dict =={}:
            return
        
        setup= self.test_handler.setups_dict[setup_name]
        if setup == None:
            print_log('Error: The setup '+ setup_name + ' was not allocated')
            raise 
        
        key= attrib
        keyval= attrib+'.'+attrib_dict[attrib]
        for tst_attr in setup.keys():
            #Check if the attribute value should be replaced
            if tst_attr == keyval:
                print_log('Attr '+attrib+' replace value '+ attrib_dict[attrib] + ' with val '+setup[tst_attr])
                attrib_dict[attrib]= setup[tst_attr]
            else:
                if tst_attr == key:
                    print_log('Attr '+attrib+' replace value '+ attrib_dict[attrib] + ' with val '+setup[tst_attr])
                    attrib_dict[attrib]= setup[tst_attr]
        
           
    def  ActionProcess(self,cover_action, main_handler_orig, child_attrib_dict_tmp):
        global test_report_action
        final_attrib_dict= {}
        print_log('Action name='+ cover_action.text)
        if cover_action.text not in self.actions_dict.keys():
            print_log("The action element is not in actions_dict")
            raise 
        
        action= copy.deepcopy(self.actions_dict[cover_action.text])
        main_handler=  copy.deepcopy(main_handler_orig )
        test_report_action = cover_action.text
        CurrTestPassed = True
        if action == None:
            print_log('Action: '+ cover_action.text + ' did not found in actions list')
            raise
       
        for attrib in action.keys():
            #Copy the action attributes into final_attrib_dict
            final_attrib_dict[attrib] = action.get(attrib)
            
        for attrib in cover_action.keys():
            final_attrib_dict[attrib] = cover_action.get(attrib)
            
            
        #Overwrite Action element attributes if necessary.
        for attrib in child_attrib_dict_tmp.keys():
            #Check if the attribute is existed in the main_handler           
            if attrib not in final_attrib_dict.keys() or self.CheckAttrbUpDownOrder(attrib, child_attrib_dict_tmp[attrib]):
                final_attrib_dict[attrib] = child_attrib_dict_tmp[attrib]
                        
        # Update target attributes
        
        if "target" in final_attrib_dict.keys():
            target_name= final_attrib_dict['target']
            exec_target=self.test_handler.targets_dict[target_name]
            main_handler.exec_target= exec_target
        
            for attrib in exec_target.attrib_dict.keys():
                if attrib not in final_attrib_dict.keys() or self.CheckAttrbUpDownOrder(attrib, main_handler.exec_target.attrib_dict[attrib])==False:
                    final_attrib_dict[attrib] = main_handler.exec_target.attrib_dict[attrib]

        # Replace attribute values due to settings in setup elements
        for attrib in final_attrib_dict.keys():
            self.AttributeUpdate_with_setup(attrib, final_attrib_dict)
            #if attrib not in main_handler.__dict__:
            #    print_log('Warning: unused attribute: '+attrib)
            main_handler.__dict__[attrib] = final_attrib_dict[attrib]
        
    
        try:
            func = action.get('func')
            main_handler.test_name= action.get('name')
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

        print_log(action.text +': ' + test_res)
     #   if hasattr(main_handler, "test_descr"):
     #       result_file.write(main_handler.test_descr+ ': ' + test_res + '\n')
     #       result_file.flush()
        return CurrTestPassed
        
        
                                    
    def     SessionProcess(self, cover_session, main_handler_orig, attrib_dict= {}, new_thread= False):    
        TestPassed = True                
        main_handler=  copy.deepcopy(main_handler_orig )
        threads= []
        session_attr= {}
        child_attrib_dict= dict(attrib_dict) 
        if cover_session.text not in self.session_dict.keys():
            print_log('Unallocated session name ' + cover_session.text)
            raise
        
        session= copy.deepcopy(self.session_dict.get(cover_session.text))
        #Combine attributes of the session with attributes of the cover session
        for attrib in session.keys():
            session_attr[attrib] = session.get(attrib)
            
        for attrib in cover_session.keys():
            session_attr[attrib]= cover_session.get(attrib)
            
        print_log('Execute session ' + session.tag)
        print_log('Attrib_dict: '+ str(attrib_dict.keys()))
        print_log('Session_dic: '+ str(session_attr.keys()))
         
        #Go through attributes and set them in the main_handler
        for attrib in session_attr.keys():
            #Check if the attribute is existed in the main_handler
            if attrib not in child_attrib_dict.keys() or  self.CheckAttrbUpDownOrder(attrib, child_attrib_dict[attrib])==False:
                child_attrib_dict[attrib] = session_attr.get(attrib)
        
        TotalTestRes = True     
        #Run the tests
        if 'iterations' in session_attr.keys():
            iterations= session_attr.get('iterations')
        else:
            iterations= 1
        
        for iter_num in range(int(iterations)):
            print_log('Session ' + cover_session.text + ' Start iteration ' + str(iter_num) + ' from ' +  str(iterations) + ' iterations')
            for child in session:
                #Add attributes if they were not added before
                child_attrib_dict_tmp = dict(child_attrib_dict)
                #send number of current iterations to child
                child_attrib_dict_tmp['iter_num']= str(iter_num)
                
                if new_thread==True:
                    if child.tag == 'thread_session':
                        child.tag= 'session'
                    if child.tag == 'thread_action':
                        child.tag = 'action'
                if child.tag == 'session':
                    TestPassed = self.SessionProcess(child , main_handler, child_attrib_dict_tmp)
                elif child.tag == 'action':
                    TestPassed = self.ActionProcess(child, main_handler, child_attrib_dict_tmp)
                elif child.tag == 'thread_session' or child.tag == 'thread_action':
                    #child, test_handler, attrib, xml_handler
                    thread_name_tmp = threading.currentThread().getName() + '.' + child.text
                    new_thread= ThreadWrapper(thread_name= thread_name_tmp, xml_handler= self, child= child, test_handler= main_handler, attrib= child_attrib_dict_tmp)
                    threads.append(new_thread)
                    new_thread.start()
                    print_log('Finish activation of thread ' + child.text) 
                
                else:
                    print_log('Wrong session element parameter '+ child.tag)
                    raise
                
                TotalTestRes = TotalTestRes and TestPassed
                
            for t in threads:
                TestPassed= t.join()
                TotalTestRes = TotalTestRes and TestPassed
            threads= []
            print_log('Session ' + cover_session.text + ' Finish iteration ' + str(iter_num) + ' from ' +  str(iterations) + ' iterations')
        print_log('Finish executing session ' + cover_session.text )
                    
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
        self.AddSetups(root)
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
    parser.add_argument('--setup', default="", type=str, help="List of emails to send result")
    parser.add_argument('--email', nargs="*", type=str, help="List of emails to send result")
    
    x = sys.argv
    del x[0]
    attrib= {}
    args = parser.parse_args(x)
    xml_handler.DataParserList(args.config)
    attrib['rel_dir'] = args.rel_dir
    rel_dir_path  = args.rel_dir
    attrib['configlistToStr']= ' '.join(map(str, args.config)) 
    if args.setup != "":
        attrib['setup']= args.setup
        
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

