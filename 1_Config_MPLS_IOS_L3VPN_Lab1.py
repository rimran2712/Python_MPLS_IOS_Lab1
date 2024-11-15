from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_scrapli.tasks import send_configs, send_command
from nornir_jinja2.plugins.tasks import template_file
from nornir_utils.plugins.tasks.data import load_yaml
import os
from rich import print
import ipdb

nr = InitNornir (config_file="Inventory/config.yaml")

# Clearing the Screen
os.system('clear')

'''
This program will configure MPLS L3VPN for Multiple Tenants
ISP using BGP free core. MPLS unicast routing being used in ISP core so ISP core network
is unaware of MP-BGP/ VPNv4 routes because VPNv4 packets will transport using MPLS.
ISP using iBGP to share VPNv4 routes, Core1  & Core2 being used as Router Reflector 
to avoiud full mesh.  
ISP using OSPF as IGP in core network to distribute labels using LDP

Variable Files: load variable from VARS(variable files), VARS are define for each host

Note: Only ISP devices (PE & Core) devices will be automate, 
CE devices supposed to be configured manually. 
'''
def config_device_interfaces_j2_template(task):
    int_cfg_template = task.run (task=template_file, template=f"config_dev_int.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_int_cfg'] = int_cfg_template.result
    dev_int_cfg_rendered = task.host['dev_int_cfg']
    dev_int_config = dev_int_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_int_config)

def config_IGP_MPLS_j2_template(task):
    igp_mpls_basic_cfg_template = task.run (task=template_file, template=f"igp_mpls_basic.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_igp_mpls_basic_cfg'] = igp_mpls_basic_cfg_template.result
    dev_igp_mpls_basic_cfg_rendered = task.host['dev_igp_mpls_basic_cfg']
    dev_igp_mpls_basic_config = dev_igp_mpls_basic_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_igp_mpls_basic_config)
    
def config_ospf_j2_template(task):
    ospf_cfg_template = task.run (task=template_file, template=f"config_dev_ospf.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_ospf_cfg'] = ospf_cfg_template.result
    dev_ospf_cfg_rendered = task.host['dev_ospf_cfg']
    dev_ospf_config = dev_ospf_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_ospf_config)

def config_iBGP_j2_template(task):
    iBGP_cfg_template = task.run (task=template_file, template=f"bgp.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_bgp_cfg'] = iBGP_cfg_template.result
    dev_bgp_cfg_rendered = task.host['dev_bgp_cfg']
    dev_bgp_config = dev_bgp_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_bgp_config)

def config_tenant_j2_template(task):
    tenant_cfg_template = task.run (task=template_file, template=f"tenant.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_tenant_cfg'] = tenant_cfg_template.result
    dev_tenant_cfg_rendered = task.host['dev_tenant_cfg']
    dev_tenant_config = dev_tenant_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_tenant_config)

def config_MPLS_L3VPN (task):
    '''
    First of all we need to load variables (vars) for hosts using load_yaml, 
    it will return yaml data and store in dictionary form and embend into dic key 
    for each specific device '''
    dev_data = task.run (task=load_yaml, file=f"./Hosts_VARS/{task.host.platform}/{task.host}.yaml")
    task.host['dev_vars'] = dev_data.result

    ''' it will return yaml data and store in dictionary form, 
    These are commond variables for all devices and used to generate 
    common configurations for all devices '''
    common_data = task.run (task=load_yaml, file=f"./Hosts_VARS/{task.host.platform}/common_vars.yaml")
    task.host['common_vars'] = common_data.result
    #Now vars are loaded, Lets configure Devices, in our lab we will configuration 

    # Configure IGP (OSPF) & MPLS LDP using j2 template
    config_IGP_MPLS_j2_template(task)

    
    # Interface level configuration (IP add, OSPF, pim etc.using j2 template
    config_device_interfaces_j2_template(task)

    # We will run IBGP on all PE & Core RR routers to exchange MPLS VPNv4 Routes
    # iBGP required TCP/IP reachability to neighbors so we 
    # have already configured IGP & MPLS labling in ISP Core
    # iBGP configuration using j2 template
    if task.host['dev_vars']['device_type'] == "core-rr" or task.host['dev_vars']['device_type'] == "pe":
        config_iBGP_j2_template(task)
    
    if task.host['dev_vars']['device_type'] == "pe":
        config_tenant_j2_template(task)
    

results = nr.run (task=config_MPLS_L3VPN)
print_result (results)
#ipdb.set_trace()