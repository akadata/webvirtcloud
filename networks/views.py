from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from computes.models import Compute
from networks.forms import AddNetPool
from vrtManager.network import wvmNetwork, wvmNetworks
from vrtManager.network import network_size
from libvirt import libvirtError


@login_required
def networks(request, compute_id):
    """
    :param request:
    :return:
    """

    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse('index'))

    error_messages = []
    compute = get_object_or_404(Compute, pk=compute_id)

    try:
        conn = wvmNetworks(compute.hostname,
                           compute.login,
                           compute.password,
                           compute.type)
        networks = conn.get_networks_info()

        if request.method == 'POST':
            if 'create' in request.POST:
                form = AddNetPool(request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    if data['name'] in networks:
                        msg = _("Pool name already in use")
                        error_messages.append(msg)
                    if data['forward'] == 'bridge' and data['bridge_name'] == '':
                        error_messages.append('Please enter bridge name')
                    try:
                        gateway, netmask, dhcp = network_size(data['subnet'], data['dhcp'])
                    except:
                        error_msg = _("Input subnet pool error")
                        error_messages.append(error_msg)
                    if not error_messages:
                        conn.create_network(data['name'], data['forward'], gateway, netmask,
                                            dhcp, data['bridge_name'], data['openvswitch'], data['fixed'])
                        return HttpResponseRedirect(reverse('network', args=[compute_id, data['name']]))
                else:
                    for msg_err in form.errors.values():
                        error_messages.append(msg_err.as_text())
        conn.close()
    except libvirtError as lib_err:
        error_messages.append(lib_err)

    return render(request, 'networks.html', locals())


@login_required
def network(request, compute_id, pool):
    """
    :param request:
    :return:
    """

    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse('index'))

    error_messages = []
    compute = get_object_or_404(Compute, pk=compute_id)

    try:
        conn = wvmNetwork(compute.hostname,
                          compute.login,
                          compute.password,
                          compute.type,
                          pool)
        networks = conn.get_networks()
        state = conn.is_active()
        device = conn.get_bridge_device()
        autostart = conn.get_autostart()
        ipv4_forward = conn.get_ipv4_forward()
        ipv4_dhcp_range_start = conn.get_ipv4_dhcp_range_start()
        ipv4_dhcp_range_end = conn.get_ipv4_dhcp_range_end()
        ipv4_network = conn.get_ipv4_network()
        fixed_address = conn.get_mac_ipaddr()
    except libvirtError as lib_err:
        error_messages.append(lib_err)

    if request.method == 'POST':
        if 'start' in request.POST:
            try:
                conn.start()
                return HttpResponseRedirect(request.get_full_path())
            except libvirtError as lib_err:
                error_messages.append(lib_err.message)
        if 'stop' in request.POST:
            try:
                conn.stop()
                return HttpResponseRedirect(request.get_full_path())
            except libvirtError as lib_err:
                error_messages.append(lib_err.message)
        if 'delete' in request.POST:
            try:
                conn.delete()
                return HttpResponseRedirect(reverse('networks', args=[compute_id]))
            except libvirtError as lib_err:
                error_messages.append(lib_err.message)
        if 'set_autostart' in request.POST:
            try:
                conn.set_autostart(1)
                return HttpResponseRedirect(request.get_full_path())
            except libvirtError as lib_err:
                error_messages.append(lib_err.message)
        if 'unset_autostart' in request.POST:
            try:
                conn.set_autostart(0)
                return HttpResponseRedirect(request.get_full_path())
            except libvirtError as lib_err:
                error_messages.append(lib_err.message)

    conn.close()

    return render(request, 'network.html', locals())
