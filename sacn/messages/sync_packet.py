# This file is under MIT license. The license file can be obtained in the root directory of this module.

"""
This implements the sync packet from the E1.31 standard.
Information about sACN: http://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf
"""
import sacn.config
from sacn.messages.root_layer import VECTOR_ROOT_E131_EXTENDED, \
    VECTOR_E131_EXTENDED_SYNCHRONIZATION, \
    RootLayer, \
    int_to_bytes, \
    make_flagsandlength


class SyncPacket(RootLayer):
    def __init__(self, cid: tuple, syncAddr: int, sequence: int = 0):
        self.syncAddr = syncAddr
        self.sequence = sequence
        super().__init__(49, cid, VECTOR_ROOT_E131_EXTENDED)

    @property
    def syncAddr(self) -> int:
        return self._syncAddr
    @syncAddr.setter
    def syncAddr(self, sync_universe: int):
        if sync_universe not in range(1, 64000):
            raise TypeError(f'sync_universe must be [1-63999]! value was {sync_universe}')
        self._syncAddr = sync_universe

    @property
    def sequence(self) -> int:
        return self._sequence
    @sequence.setter
    def sequence(self, sequence: int):
        if sequence not in range(0, 256):
            raise TypeError(f'Sequence is a byte! values: [0-255]! value was {sequence}')
        self._sequence = sequence
    def sequence_increase(self):
        self._sequence += 1
        if self._sequence > 0xFF:
            self._sequence = 0

    def getBytes(self) -> tuple:
        rtrnList = super().getBytes()
        if sacn.config.corrupt_acn_sync_pid:
            rtrnList[9] = 0x00
        rtrnList.extend(make_flagsandlength(self.length - 38))
        rtrnList.extend(VECTOR_E131_EXTENDED_SYNCHRONIZATION)

        seqNum = (self._sequence + sacn.config.offset_sync_seq_num) % 256
        rtrnList.append(seqNum)
        # Hook to offset sync address if desired.
        rtrnList.extend(int_to_bytes(self._syncAddr + sacn.config.offset_sync_packet_universe_num))
        rtrnList.extend((0, 0))  # the empty reserved slots

        # Hooks to corrupt various parts of the sync packet.
        if sacn.config.corrupt_root_preamble_sync:
            rtrnList[1] = 0x01
        if sacn.config.corrupt_root_vector_sync:
            rtrnList[21] = 0x10
        if sacn.config.corrupt_framing_vector_sync:
            rtrnList[42] = 0x11
        return tuple(rtrnList)

    @staticmethod
    def make_sync_packet(raw_data) -> 'SyncPacket':
        """
        Converts raw byte data to a sACN SyncPacket. Note that the raw bytes have to come from a 2016 sACN Message.
        :param raw_data: raw bytes as tuple or list
        :return: a SyncPacket with the properties set like the raw bytes
        """
        # Check if the length is sufficient
        if len(raw_data) < 47:
            raise TypeError('The length of the provided data is not long enough! Min length is 47!')
        # Check if the three Vectors are correct
        if tuple(raw_data[18:22]) != tuple(VECTOR_ROOT_E131_EXTENDED) or \
           tuple(raw_data[40:44]) != tuple(VECTOR_E131_EXTENDED_SYNCHRONIZATION):
            # REMEMBER: when slicing: [inclusive:exclusive]
            raise TypeError('Some of the vectors in the given raw data are not compatible to the E131 Standard!')
        tmpPacket = SyncPacket(cid=raw_data[22:38], syncAddr=(0xFF * raw_data[45]) + raw_data[46])
        tmpPacket.sequence = raw_data[44]
        return tmpPacket
