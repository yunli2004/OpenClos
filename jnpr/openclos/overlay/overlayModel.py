'''
Created on Nov 23, 2015

@author: yunli

'''
import uuid
from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, Enum, UniqueConstraint, Index, Boolean
from sqlalchemy.orm import relationship, backref

from jnpr.openclos.loader import OpenClosProperty
if OpenClosProperty().isSqliteUsed():
    from sqlalchemy import BLOB
else:
    from sqlalchemy.dialects.mysql import MEDIUMBLOB as BLOB
from jnpr.openclos.model import ManagedElement, Base

class OverlayDevice(ManagedElement, Base):
    __tablename__ = 'overlayDevice'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    role = Column(Enum('spine', 'leaf'))
    address = Column(String(60))
    routerId = Column(String(60))
    overlay_fabrics = relationship(
        'OverlayFabric',
        secondary='overlayFabricOverlayDeviceLink'
    )

    def __init__(self, name, description, role, address, routerId):
        '''
        Creates device object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.role = role
        self.address = address
        self.routerId = routerId
        
    def update(self, name, description, role, address, routerId):
        '''
        Updates device object.
        '''
        self.name = name
        self.description = description
        self.role = role
        self.address = address
        self.routerId = routerId
    
class OverlayFabric(ManagedElement, Base):
    __tablename__ = 'overlayFabric'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(String(256))
    overlayAS = Column(BigInteger)
    routeReflectorAddress = Column(String(60))

    overlay_devices = relationship(
        'OverlayDevice',
        secondary='overlayFabricOverlayDeviceLink'
    )
    
    def __init__(self, name, description, overlayAS, routeReflectorAddress, devices):
        '''
        Creates Fabric object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.overlayAS = overlayAS
        self.routeReflectorAddress = routeReflectorAddress
        for device in devices:
            self.overlay_devices.append(device)

    def getUrl(self):
        return "/fabrics/" + self.id
    
    def update(self, name, description, overlayAS, routeReflectorAddress, devices):
        '''
        Updates Fabric object.
        '''
        self.name = name
        self.description = description
        self.overlayAS = overlayAS
        self.routeReflectorAddress = routeReflectorAddress
        for device in devices:
            self.overlay_devices.append(device)
    
    def clearDevices(self):
        '''
        Remove existing devices
        '''
        del self.overlay_devices[:]
    
class OverlayFabricOverlayDeviceLink(ManagedElement, Base):
    __tablename__ = 'overlayFabricOverlayDeviceLink'
    overlay_fabric_id = Column(String(60), ForeignKey('overlayFabric.id'), primary_key=True)
    overlay_device_id = Column(String(60), ForeignKey('overlayDevice.id'), primary_key=True)

class OverlayTenant(ManagedElement, Base):
    __tablename__ = 'overlayTenant'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    overlay_fabric_id = Column(String(60), ForeignKey('overlayFabric.id'), nullable=False)
    overlay_fabric = relationship("OverlayFabric", backref=backref('overlay_tenants', order_by=name, cascade='all, delete, delete-orphan'))
    __table_args__ = (
        Index('overlay_fabric_id_overlay_tenant_name_uindex', 'overlay_fabric_id', 'name', unique=True),
    )

    def __init__(self, name, description, overlay_fabric):
        '''
        Creates Tenant object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.overlay_fabric = overlay_fabric
        
    def update(self, name, description):
        '''
        Updates Tenant object.
        '''
        self.name = name
        self.description = description
    
class OverlayVrf(ManagedElement, Base):
    __tablename__ = 'overlayVrf'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    routedVnid = Column(Integer)
    loopbackAddress = Column(String(60))
    loopbackCounter = Column(Integer)
    overlay_tenant_id = Column(String(60), ForeignKey('overlayTenant.id'), nullable=False)
    overlay_tenant = relationship("OverlayTenant", backref=backref('overlay_vrfs', order_by=name, cascade='all, delete, delete-orphan'))
    __table_args__ = (
        Index('overlay_tenant_id_overlay_vrf_name_uindex', 'overlay_tenant_id', 'name', unique=True),
    )

    def __init__(self, name, description, routedVnid, loopbackAddress, overlay_tenant):
        '''
        Creates VRF object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.routedVnid = routedVnid
        self.loopbackAddress = loopbackAddress
        self.overlay_tenant = overlay_tenant
        
    def getUrl(self):
        return "/vrfs/" + self.id
    
    def update(self, name, description, routedVnid, loopbackAddress):
        '''
        Updates VRF object.
        '''
        self.name = name
        self.description = description
        self.routedVnid = routedVnid
        self.loopbackAddress = loopbackAddress
        
    def getDevices(self, role=None):
        if self.overlay_tenant and self.overlay_tenant.overlay_fabric:
            if not role:
                return self.overlay_tenant.overlay_fabric.overlay_devices
            else:
                return [dev for dev in self.overlay_tenant.overlay_fabric.overlay_devices if dev.role == role]
        
        return []
    def getSpines(self):
        return self.getDevices("spine")
    def getLeafs(self):
        return self.getDevices("leaf")
    
class OverlayNetwork(ManagedElement, Base):
    __tablename__ = 'overlayNetwork'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    vlanid = Column(Integer)
    vnid = Column(Integer)
    pureL3Int = Column(Boolean)
    overlay_vrf_id = Column(String(60), ForeignKey('overlayVrf.id'), nullable=False)
    overlay_vrf = relationship("OverlayVrf", backref=backref('overlay_networks', order_by=name, cascade='all, delete, delete-orphan'))
    __table_args__ = (
        Index('overlay_vrf_id_overlay_network_name_uindex', 'overlay_vrf_id', 'name', unique=True),
    )

    def __init__(self, name, description, overlay_vrf, vlanid, vnid, pureL3Int):
        '''
        Creates network object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.overlay_vrf = overlay_vrf
        self.vlanid = vlanid
        self.vnid = vnid
        self.pureL3Int = pureL3Int
        
    def update(self, name, description, vlanid, vnid, pureL3Int):
        '''
        Updates network object.
        '''
        self.name = name
        self.description = description
        self.vlanid = vlanid
        self.vnid = vnid
        self.pureL3Int = pureL3Int
    
class OverlaySubnet(ManagedElement, Base):
    __tablename__ = 'overlaySubnet'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    cidr = Column(String(60))
    overlay_network_id = Column(String(60), ForeignKey('overlayNetwork.id'), nullable=False)
    overlay_network = relationship("OverlayNetwork", backref=backref('overlay_subnets', order_by=name, cascade='all, delete, delete-orphan'))
    __table_args__ = (
        Index('overlay_network_id_overlay_subnet_name_uindex', 'overlay_network_id', 'name', unique=True),
    )

    def __init__(self, name, description, overlay_network, cidr):
        '''
        Creates subnet object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.overlay_network = overlay_network
        self.cidr = cidr
        
    def update(self, name, description, cidr):
        '''
        Updates subnet object.
        '''
        self.name = name
        self.description = description
        self.cidr = cidr
    
class OverlayL3port(ManagedElement, Base):
    __tablename__ = 'overlayL3port'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    overlay_subnet_id = Column(String(60), ForeignKey('overlaySubnet.id'), nullable=False)
    overlay_subnet = relationship("OverlaySubnet", backref=backref('overlay_l3ports', order_by=name, cascade='all, delete, delete-orphan'))
    __table_args__ = (
        Index('overlay_subnet_id_overlay_l3port_name_uindex', 'overlay_subnet_id', 'name', unique=True),
    )

    def __init__(self, name, description, overlay_subnet):
        '''
        Creates L3 port object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.overlay_subnet = overlay_subnet
        
    def update(self, name, description):
        '''
        Updates L3 port object.
        '''
        self.name = name
        self.description = description
    
class OverlayL2port(ManagedElement, Base):
    __tablename__ = 'overlayL2port'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    interface = Column(String(100), nullable=False)
    overlay_ae_id = Column(String(60), ForeignKey('overlayAe.id'))
    overlay_ae = relationship("OverlayAe", backref=backref('overlay_members', order_by=name, cascade='all, delete, delete-orphan'))
    overlay_network_id = Column(String(60), ForeignKey('overlayNetwork.id'), nullable=False)
    overlay_network = relationship("OverlayNetwork", backref=backref('overlay_l2ports', order_by=name, cascade='all, delete, delete-orphan'))
    overlay_device_id = Column(String(60), ForeignKey('overlayDevice.id'), nullable=False)
    overlay_device = relationship("OverlayDevice", backref=backref('overlay_l2ports', order_by=name, cascade='all, delete, delete-orphan'))
    __table_args__ = (
        #Index('overlay_ae_id_overlay_l2port_name_uindex', 'overlay_ae_id', 'name', unique=True),
        Index('overlay_network_id_overlay_l2port_name_uindex', 'overlay_network_id', 'name', unique=True),
        Index('overlay_device_id_overlay_l2port_name_uindex', 'overlay_device_id', 'name', unique=True),
    )

    def __init__(self, name, description, interface, overlay_network, overlay_device, overlay_ae=None):
        '''
        Creates L2 port object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.interface = interface
        self.overlay_network = overlay_network
        self.overlay_device = overlay_device
        self.overlay_ae = overlay_ae
        
    def update(self, name, description, interface):
        '''
        Updates L2 port object.
        '''
        self.name = name
        self.description = description
        self.interface = interface
    
class OverlayAe(ManagedElement, Base):
    __tablename__ = 'overlayAe'
    id = Column(String(60), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(256))
    esi = Column(String(60), nullable=False)
    lacp = Column(String(60), nullable=False)

    def __init__(self, name, description, esi, lacp):
        '''
        Creates aggregated interface object.
        '''
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.esi = esi
        self.lacp = lacp
        
    def update(self, name, description, esi, lacp):
        '''
        Updates L2 port object.
        '''
        self.name = name
        self.description = description
        self.esi = esi
        self.lacp = lacp

class OverlayDeployStatus(ManagedElement, Base):
    __tablename__ = 'overlayDeployStatus'
    id = Column(String(60), primary_key=True)
    configlet = Column(BLOB)
    object_url = Column(String(1024), nullable=False)
    operation = Column(String(60))
    overlay_device_id = Column(String(60), ForeignKey('overlayDevice.id'), nullable=False)
    overlay_device = relationship("OverlayDevice", backref=backref('deploy_status', cascade='all, delete, delete-orphan'))
    overlay_vrf_id = Column(String(60), ForeignKey('overlayVrf.id'))
    overlay_vrf = relationship("OverlayVrf", backref=backref('deploy_status', cascade='all, delete, delete-orphan'))
    status = Column(Enum('unknown', 'progress', 'success', 'failure'), default='unknown')
    statusReason = Column(String(1024))
    __table_args__ = (
        Index('object_url_overlay_device_id_uindex', 'object_url', 'overlay_device_id', unique=True),
    )
    
    def __init__(self, configlet, object_url, operation, overlay_device, overlay_vrf=None, status=None, statusReason=None):
        '''
        Creates status object.
        '''
        self.id = str(uuid.uuid4())
        self.configlet = configlet
        self.object_url = object_url
        self.operation = operation
        self.overlay_device = overlay_device
        self.overlay_vrf = overlay_vrf
        self.status = status
        self.statusReason = statusReason
        
    def update(self, status, statusReason, operation):
        '''
        Update status object.
        '''
        self.status = status
        self.statusReason = statusReason
        self.operation = operation
        