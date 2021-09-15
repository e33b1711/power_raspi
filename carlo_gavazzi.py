import logging

import device
import probe
from register import *

log = logging.getLogger()

class Reg_ver(Reg, int):
    def __init__(self, base, name):
        Reg.__init__(self, base, 1, name)

    def __int__(self):
        v = self.value
        return v[0] << 16 | v[1] << 8 | v[2]

    def __str__(self):
        return '%d.%d.%d' % self.value

    def decode(self, values):
        v = values[0]
        return self.update((v >> 12, v >> 8 & 0xf, v & 0xff))

nr_phases = [ 3, 3, 2, 1, 3 ]

phase_configs = [
    '3P.n',
    '3P.1',
    '2P',
    '1P',
    '3P',
]

switch_positions = [
    'kVARh',
    '2',
    '1',
    'Locked',
]

class EM24_Meter(device.EnergyMeter):
    productid = 0xb017
    productname = 'Carlo Gavazzi EM24 Ethernet Energy Meter'
    min_timeout = 0.5

    def __init__(self, *args):
        super(EM24_Meter, self).__init__(*args)

        self.info_regs = [
            Reg_ver( 0x0302, '/HardwareVersion'),
            Reg_ver( 0x0303, '/FirmwareVersion'),
            Reg_u16( 0x1102, '/PhaseConfig', text=phase_configs, write=(0, 4)),
            Reg_u16( 0x1102, '/Serial'),
        ]

    def phase_regs(self, n):
        s = 2 * (n - 1)
        return [
            Reg_s32l(0x0000 + s, '/Ac/L%d/Voltage' % n,        10, '%.1f V'),
            Reg_s32l(0x000c + s, '/Ac/L%d/Current' % n,      1000, '%.1f A'),
            Reg_s32l(0x0012 + s, '/Ac/L%d/Power' % n,          10, '%.1f W'),
            Reg_s32l(0x0046 + s, '/Ac/L%d/Energy/Forward' % n, 10, '%.1f kWh'),
        ]

    def device_init(self):
        # make sure application is set to H
        appreg = Reg_u16(0x1101)
        if self.read_register(appreg) != 7:
            self.write_register(appreg, 7)

            # read back the value in case the setting is not accepted
            # for some reason
            if self.read_register(appreg) != 7:
                log.error('%s: failed to set application to H', self)
                return

        self.read_info()

        phases = nr_phases[int(self.info['/PhaseConfig'])]

        regs = [
            Reg_s32l(0x0028, '/Ac/Power',          10, '%.1f W'),
            Reg_u16( 0x0037, '/Ac/Frequency',      10, '%.1f Hz'),
            Reg_s32l(0x003E, '/Ac/Energy/Forward', 10, '%.1f kWh'),
            Reg_s32l(0x005C, '/Ac/Energy/Reverse', 10, '%.1f kWh'),
            Reg_u16( 0x0304, '/SwitchPos', text=switch_positions),
        ]

        if phases == 3:
            regs += [
                Reg_mapu16(0x0032, '/PhaseSequence', { 0: 0, 0xffff: 1 }),
            ]

        for n in range(1, phases + 1):
            regs += self.phase_regs(n)

        self.data_regs = regs

    def dbus_write_register(self, reg, path, val):
        super(EM24_Meter, self).dbus_write_register(reg, path, val)
        self.sched_reinit()

    def get_ident(self):
        return 'cg_%s' % self.info['/Serial']

models = {
    1648: {
        'model':    'EM24DINAV23XE1X',
        'handler':  EM24_Meter,
    },
    1649: {
        'model':    'EM24DINAV23XE1PFA',
        'handler':  EM24_Meter,
    },
    1650: {
        'model':    'EM24DINAV23XE1PFB',
        'handler':  EM24_Meter,
    },
    1651: {
        'model':    'EM24DINAV53XE1X',
        'handler':  EM24_Meter,
    },
    1652: {
        'model':    'EM24DINAV53XE1PFA',
        'handler':  EM24_Meter,
    },
    66: {
        'model':    'EM24DINAV53XAAAAA',
        'handler':  EM24_Meter,
    },
}

probe.add_handler(probe.ModelRegister(0x0302, models,
                                      methods=['tcp'],
                                      units=[1]))
