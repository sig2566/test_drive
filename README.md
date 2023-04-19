# test_drive
Automation environment for SW build and verification.
This directory contains scripts, using for software automatic formal build, release and verification. 
The framework is suitable for development for verification of the embedded systems.

## Script for the release build and validation
###  Main features
* Support automation for prepare the internal and external release components. It includes build and packaging and copy operation.
* Support automatic running unit tests for the release validation. The tests can be running on different platforms: VM, ARM boards, native Linux
* Flexibility. It is possible to reuse the same test for different devices
* Simplicity.
* Ability for simple integration with external release generation tools like SW packager and Jenkins
* Support running tests on different platforms.
* Support simple updating the script in the future.
###  Command line
This is python script with the following parameters:
```
python3 test_drive.py –tst <list of names of test and build sessions> --config <list of XML configuration files> --rel_dir <release deploy directory> --setup <setup name>
```
**PASS/FAIL indication:** 
The script prints: “Automation test passed” in good case and “Automation test failed” in bad case in the last stdoutput line.

####  Configure scenario to run
User may configure what the script does by selection of the corresponding session name from the XML configuration file. The –tst flag is used to select the names of the sessions to run.

####  Configure build deployment path.
User may select the path to put the release build with using –rel_dir flag, following with the path to the release directory.

####  Selection setup.
The setup is specific set of parameters, like IPs, passwords, users, which are used by specific hardware tests setup.
####  Selection XML configuration files
User may use number of configuration files to configure the script. The list of xml configuration files is added with the –config flag.



####  XML configuration files
XML configuration files can contain the following main elements:
#####  Command Elements
The command element represent the command, which sent to output stream. The command might have optional attributes and the command body. Format of the command element:
```
<cmd  --- Command element tag  
    attributes
 >
    Body
 </cmd> 
```
**Attributes:** 
chk= "True"   ---- Call exception if the command failed with error.  
**final**=”.”  -- Immediately finish the command and go to the next command  
**final**=”regular expression”  -- The command is finished when the regular expression pattern appeared in the output of the command  
**pass**=”pass_regular_expression” – The pass pattern. When the running command output contains the pass patter, the command result is passed.
  
The following two attributes are used to set and handle timeouts after the command execution start:  
**action_delay** – Waiting time in seconds before the action is started. Default is 1 second.  
**timeout_action** –Activation of some action after the timeout is expired:  
* “new_line” – Print new line periodically every action_delay time..  
* “exception” – run exception.  
* “exit” – Finish when the time is expired.  
NOTE: If the **final** and **timeout_action** attributes are not defined, then the **`echo special_tag`** command is sent after the command and the command handler waits for the **special_tag** as indication that the previous command was finished.  
   
#####  Command body
The command body is the Python stile line. The obj object contains may be user in the line as parameter. Its fields are attributes, defined in upper XML elements.   
Example:   
```
<cmd final="."> 'rauc status mark-active ' + obj.bank </cmd>   
<cmd final="password"> 'login ' + obj.user </cmd>
```
#####  Targets
Target is an XML element, containing information how to access to the remote target to run build or test.  
Example of target definition:  
```   
<target 
    name="UEP_UTL_14_132" 
       ip="172.16.14.132" 
    uid="root" 
    passw="root" 
    info="UTL test board" 
    > 
    <prolog> 
    	<cmd>'echo Connection with UEP_UTL_14.132 board started'</cmd> 
     </prolog> 
    <epilog> 
     	<cmd>'echo Connection Finished'</cmd> 
    </epilog> 
</target>
```
  Where: #name# is the target name, #ip, uid, passw# – parameters for SSH session establishment.  
prolog – list of Linux instructions, implemented on the target after connection  
epilog – list of Linux instructions, implemented on the target before disconnect ssh session.   
#####  Setups
The setup is representation of the specific test environment. It includes number different parameters, used together in the setups. For example they may be IPs, uids, passwords, etc. The setup is used to replace general attributes values in the XML elements to specific values per setup. Example:  
```
<setup
 name="BOARD_172.16.15.186"
 >

 <attrib
  id="ip"
  new_val="172.16.15.186"
  />
  
  <attrib
  id="target_ip"
  val="TARGET_IP"
  new_val="172.16.15.186"
  />
…………………………………………………………………..  
  <attrib
  id="bundle_name"'
  new_val="swupdate_uep2025.raucb"
  />
   
 </setup>
```
#####  Actions. 
The action elements describe some automation operation like run/ build/test. Every action element contains information about build/test action, its attributes and remote targets, which are used to run the action. Actions are divided to two types:
* Simple action. Simple action is implemented by direct python function. It is necessary to implement complicated debugging/ build actions. Example:
```	
     <action
		name= "alive_wait"
		func= "ping_alive_test"
	>
     </action>
 
     <action
		name= "random_delay"
		func= "random_delay"
		start_time= "20"
		end_time="40"
   >
  </action>
```
 The **func** is the name of the python function, implementing this action.
* Complex actions. The list of the Linux commands, which should be executed on the target to run the action, is implemented directly in the action XML element:
 ``` 
 <action
		name= "iss_tftp_upgrade_immediate_activate_test"
		func= "exec_cmdlist"
		protocol_ip="tftp://172.16.15.61/"
		bundle_name = "/swupdate.raucb"
	>
		<cmd final= "ISS#" pass="Installing .* succeeded"
		> 'firmware download ' + obj.protocol_ip + obj.bundle_name</cmd>
		<cmd final= "Are you sure you want to perform firmware activate procedure?" 
		     > 'firmware activate immediate database migrate on'</cmd>		     
			<cmd final="The system is going down for reboot NOW!"
			>'Y'</cmd>
  </action>
```
Example:
 The **cmd** XML element defines the Linux command, executed on target. The **`<cmd>`** element has the following special features:
1. The **cmd** Linux command can be treated as python string commands. It can use the action and sessions attributes the command.
2. It is possible to add checking of the error code. If the commands returns error code then exception is raised (chk attribute). Example chk=”True”
3. It is possible check result of the operation with checking if some patterns is existed in output data (pass attribute)  pass=”Passed”
4. The final attribute specifies the final string of the command.
5. The command execution behavior in the case of timeout expired:
  a. action_delay= "120" – Wait for N seconds with the command execution before some action.
  b. timeout_action="exit" | "new_line" | "exception" – Actions after timeout happen.
  
#####  Sessions. 
A session is XML element, which is used to define complicated test/build scenarios. Every session may contain other sessions, actions and attributes. Using these parameters user may specify complicated build and test scenario. The session XML element can contains attributes, actions and other sessions. The inner actions and sessions are executed by their order. All attributes are passed from outer session into internal sessions and actions.
Example of session:
```
  <!-- ISS immideate upgrade from tftp server -->
  <session
        name="ISS_IMMIDEATE_UPGRADE_TFTP_TST"
        host = "build_VM_61"
        target="UEP_UTL_14_132_ISS"
		timeout= "4600"
        iterations= "1"
         >
        <action>iss_tftp_upgrade_immediate_activate_test</action>
        <action>alive_wait</action>		
        <session>ISS_VERSION_TST</session>
     </session>    '

	 '	<!-- ISS immideate upgrade from sftp server -->
      <session
        name="ISS_IMMIDEATE_UPGRADE_SFTP_TST"
        protocol_ip= "sftp://root:devops123@172.16.15.61//mnt/80GB/opt/"
        iterations="100"
         >
        <session>ISS_IMMIDEATE_UPGRADE_TFTP_TST</session>
     </session>
```
You can see that the session ISS_IMMIDEATE_UPGRADE_SFTP_TST uses the session ISS_IMMIDEATE_UPGRADE_TFTP_TST and the difference is only upload protocol.



NOTE: If there are number XML files, then the script combines the data from all files.

#####  Support Multi-threading
It is possible to run number session and actions in parallel. It is necessary to use the elements thread_session and thread_action inside the upper session to run  them in parallel in the separate thread. Example:
```
  <session
        name="LINUX_SW_UPDATE_ISS_RACE_TST"
        host = "build_VM_61"
		timeout= "9600"
        iterations= "1"
        >
        <thread_session target="UEP_UTL_14_132" ip= "172.16.14.131"
	        start_time="120"
	        end_time="180"         
	        >RANDOM_DELAY_REBOOT</thread_session>
        <thread_session target="UEP_UTL_14_132_ISS">ISS_IMMIDEATE_UPGRADE_TFTP_TST_UEP2025_131</session>	
        <session target="UEP_UTL_14_132_ISS" ip="172.16.14.131" >ISS_VERSION_TST</session>	
     </session>  
```
####  Extension and Reusing of test_drive components
The test_drive verification system is highly extensible. It is possible to re-use existed components to build automation test. 
#####  Definition the automation test using XML elements.
The relations between using XML elements are presenting on the picture below: 
























It is possible to extend the automation with definition of complex upper sessions, including number inner sessions, actions, threads.

####  Flexibility with Attributes
Attributes provide additional option to modify/extend the test. The test actions use XML attributes to customize the execution. There are number ways to modify attributes. See these methodologies in the sections below.

#####  Up to down attributes modification
Every session and action XML element may contain number of attributes. There are the following rules for attribute use:
* If attribute is defined in the external (upper) session/action elements that it is passed to all internal sessions and actions. It the same attribute is defined in the internal session/action, that its value is changed to with the value of the same attribute, deined in the external session.
Example:
In this example the value GENERAL_HOST is replaced with build_VM_61  
```	  
  <session  
		name=”name1”  
		host=”GENERAL_HOST”  
       >
	 
      </session>  
<session  
        name="LINUX_SW_UPDATE_ISS_RACE_TST"  
        host = "build_VM_61"  
       timeout= "9600"  
        iterations= "1"  
        >  
       <session >name1</session>  
</session>
```
* If attribute is defined into the child element of the session that it is applied to that child element. 
    Example:
In this example the RANDOM_DELAY_REBOOT session gets start_time="120" and end_time="180" attributes.  
```
<session
        name="LINUX_SW_UPDATE_ISS_RACE_TST"

        >
        <thread_session target="UEP_UTL_14_132" ip= "172.16.14.131"
	        start_time="120"
	        end_time="180"         
	        >RANDOM_DELAY_REBOOT
	</thread_session>
</session>	
```	
* If the same attribute is defined in external session and in the inner session/action elements, including into that session, that the value is taken from the upper session. There are exceptions of the assigned order is defined in the method XML_handler. CheckAttrbUpDownOrder. Currently the inner value is taken for the following attributes:
* iterations – It defines number times the current session should run.  
* timeout – Maximal number seconds, needed for running of some action.  
* The attributes of the target element are used as the action XML element attributes.
* During the test run, the attributes and their values are added as parameters of the MainHandler class and they are used for the **actio** execution. For example in the case of compound actions it may used in the **cmd** element. Example:  
```
  <action
		name= "iss_tftp_upgrade_immediate_activate_test"
		func= "exec_cmdlist"
		protocol_ip="tftp://172.16.15.61/"'
		bundle_name = "swupdate.raucb"
		>
		<cmd final= "ISS#" pass="Installing .* succeeded"
	> 'firmware download ' + obj.protocol_ip +  obj.bundle_name
         '  </cmd>
		<cmd final= "Are you sure you want to perform firmware activate procedure?" 
		     > 'firmware activate immediate database migrate on'</cmd>		     
			<cmd final="The system is going down for reboot NOW!"
			>'Y'</cmd>
	</action>'
```
#####  Updating attributes using setups
The setup element is used to define replacement for group of elements. It is useful to define some test setups, which may include number boards, servers, etc. working together. Every setup contains attributes, their new values and optional their previous values. If the action element has its value and name, similar with defined in the set, than the value is replaced with the new value from the setup element  
Example:  
In the example below the ip attribute value is replaced from SERIAL_IP to 172.16.13.128  
```
<setup
 name="BOARD_172.16.15.186"
 >
……………………………………………………..
  <attrib
  id="ip"
  val="SERIAL_IP"
  new_val="172.16.13.128"
  />
…………………………………….
</setup>

  <target
    name="UEP_SERIAL"
	ip="SERIAL_IP"
    uid="root"
    passw="devops123"
    info="UTL test board"
    >
    <prolog>
    	………………………………
     </prolog>
    <epilog>
     	<cmd final=".">'echo Connection Finished'</cmd>
    </epilog>
  
  </target>'
```
#####  CMD element attributes.
The “cmd” elements may have attributes, using for command execution processing. These attributes are not controlled bythe regular action attributes, but their value may be replaced by value.  
Example:  
In this example the pass attribute of the cmd element gets the “EVENT” value  
```
  <action name= "recovery_iss"
 			func= "exec_cmdlist"
 			target="UEP_SERIAL"
 			timeout= "19600"
 			FINAL_STR_RESTART="ISS failed first time. Restart ISS"
 	>
 		<cmd final=".">'cd /opt/uep/apps'</cmd>
 		<cmd final=".">'cp iss.conf iss_bkp.conf'</cmd>
 		<cmd  pass="FINAL_STR_RESTART"
 		     final= "rauc status: marked slot">'killall -9 ISS.exe'</cmd>
……………………………..
        </action>
   <session name= "SYSTEM_RECOVERY_TEST"
   ……………………………………..
    >
    ………………………………………………………………..
   	 <action FINAL_STR_RESTART="EVENT">recovery_iss</action>
…………………………………………………………………..
   	 
   	</session>
```
“Common Attributes  
The common attributes are hardcoded. They are used for most common issues. They are presented in the table below:  

Name  | Description | Default
target| The name of the target. It is used to selection the corresponding target.| “”
mode |Compilation mode (release or debug) |release
exec_path| Path on the target computer, where binaries release files should be located and executed. |“.”
timeout | Restrict the time of the test running on target (secs) | 300
rel_dir | Release directory. This parameter is set with command line |/tmp/PHY_RELEASE
tests_path | Path to reference files on disk p. | " "
host |Name of the host server. |‘’
host_path | Path to working directory on host server |‘.’
host_sitch |Configure the action to switch temporary from target to host server, for example for the test/release deployment (“True”, “False”)| “False”

#####  Using multiple XML files
User may use number XML files to keep the tests to use only necessary tests. The test_drive script uses the definitions from all XML files including with –config list.

#####  Extention of the main classes.
It is very simple to extend the test_drive python classes with additional functionality.  See as example the enos_tests.py file:
* Import the test_drive file:  
import **test_drive** 
	
* Create new file, which inherited from the corresponding main class:
```
class ENOS_main_handler(test_drive.MainHandler):
    def __init__(self, exec_target):
        self.swupdate_file= 'swupdate.raucb'
        super().__init__(exec_target)
         
    def get_current_partition(self):
        self.CommonSetup()        
        self.exec_target.close_connection()
        return True
…………………………………..
```
* Create the start commands, which uses new class and run existed start procedure: 
```
exec_target= test_drive.ExecTarget()                
test_handler = ENOS_main_handler(exec_target)
#exec_target.add_parent_class_callback(test_handler)
xml_handler= test_drive.XML_handler(test_handler)
test_drive.test_processing(xml_handler)	
```
####  Use Cases


#####  Build and test commands examples
```
Test switch partitions in Linux 
test_drive.py --config build_config.xml enos_config.xml --tst SWITCH_PARTITIONS_TST  --rel_dir  . --setup BOARD_172.16.15.186

Test SW update in Linux 
test_drive.py  --config build_config.xml enos_config.xml --tst LINUX_SW_UPDATE_FULL_TST  --rel_dir .  --setup BOARD_172.16.15.186 

ISS partitions upgrade tests: 
test_drive.py --config build_config.xml enos_config.xml --tst SWITCH_PARTITIONS_TST  --rel_dir .  --setup BOARD_172.16.15.186 

RAUC fault test: 
test_drive.py --config build_config.xml enos_config.xml enos_iss_config.xml  --tst LINUX_SW_UPDATE_RACE_TST  --rel_dir . --setup BOARD_172.16.15.186 
```
#####  Customization of the build & test environment
User may change the general tests behavior. For example it can select running tests/build on private VM. In that case user may add new personal config file with additional options.



