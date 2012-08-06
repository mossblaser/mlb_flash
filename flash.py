#!/usr/bin/env python

"""
Flash programmer for the lab boards
"""

from serial import Serial

from textwrap import wrap


def i2b(num, num_bytes):
	"""
	Convert a number into bytes
	"""
	out = ""
	for byte in range(num_bytes):
		out += chr(num & 0xFF)
		num >>= 8
	return out


def b2i(data):
	"""
	Convert a stream of bytes into a number
	"""
	out = 0
	for char in data[::-1]:
		out <<= 8
		out |= ord(char)
	return out


# Conversion of numbers into various length byte streams
def byte(num): return i2b(num, 1)
def half(num): return i2b(num, 2)
def word(num): return i2b(num, 4)
def dblw(num): return i2b(num, 8)


class FlashException(Exception):
	pass


class Flash(object):
	
	MAGIC_CHALLENGE = "\xFE\xA5\x1B\x1E"
	MAGIC_RESPONSE  = "\xFE\xE1\x90\x0D"
	
	# Number of bytes sent before an ack
	ACK_PERIOD = 16
	
	def __init__(self, *args, **kwargs):
		"""
		Connect to the board. Accepts the same arguments as the PySerial object.
		"""
		self.serial = Serial(*args, **kwargs)
		
		self.check_connection()
	
	
	def check_connection(self):
		"""
		Check the board is responding and is ready to be programmed!
		"""
		
		# Send the magic number
		self.write(Flash.MAGIC_CHALLENGE)
		if self.read(4) != Flash.MAGIC_RESPONSE:
			raise FlashException("Board not responding!")
	
	
	def get_rom_id(self):
		"""
		Get the board's ROM info
		"""
		self.write("I")
		manufacturer_code = b2i(self.read(1))
		part_code         = b2i(self.read(1))
		
		return (manufacturer_code, part_code)
	
	
	def ping(self):
		"""
		Ping the board
		"""
		self.write("P")
		resp = self.read(1)
		if resp != "A":
			raise FlashException("Ping response 'A' expected, got %s"%(repr(resp)))
	
	
	def erase(self, address):
		"""
		Erase an area of ROM containing the address given.
		"""
		self.write("E")
		self.write(word(address))
		resp = self.read(1)
		if resp != "A":
			raise FlashException("Erase response 'A' expected, got %s"%(repr(resp)))
	
	
	def get_ack(self):
		"""
		Read an ack from the board.
		"""
		ack = self.read(1)
		if ack != "A":
			raise FlashException("Acknowledge 'A' expected, got %s"%(repr(ack)))
	
	
	def send_ack(self):
		"""
		Send an to the board.
		"""
		self.write("A")
	
	
	def rom_read(self, address, length):
		"""
		Read from the ROM
		"""
		return "".join(self.rom_read_(address, length))
	
	def rom_read_(self, address, length):
		"""
		Read from the ROM (yields each 16-byte block)
		"""
		self.write("R")
		self.write(word(address))
		self.write(word(length))
		
		data = ""
		read_bytes = 0
		while read_bytes < length:
			data += self.read(1)
			read_bytes += 1
			
			# Get the ack when needed
			if read_bytes % Flash.ACK_PERIOD == 0:
				self.send_ack()
				yield data
				data = ""
		
		# Get the final ack
		if read_bytes % Flash.ACK_PERIOD != 0:
			self.send_ack()
			yield data
		
		return
	
	
	def rom_write(self, address, data):
		"""
		Write to the ROM
		"""
		for _ in self.rom_write_(address, data):
			pass
	
	
	def rom_write_(self, address, data):
		"""
		Write to the ROM
		"""
		self.write("W")
		self.write(word(address))
		self.write(word(len(data)))
		
		while data:
			block = data[:Flash.ACK_PERIOD]
			data  = data[Flash.ACK_PERIOD:]
			self.write(block)
			yield len(block)
			self.get_ack()
	
	
	def write(self, data):
		"""
		Send bytes to the board.
		"""
		self.serial.write(data)
	
	
	def read(self, length):
		"""
		Read a certain number of bytes from the board (or fail if timeout)
		"""
		data = self.serial.read(length)
		if len(data) != length:
			raise FlashException("Expected %d bytes, got %d."%(length, len(data)))
		
		return data
	
	
	def close(self):
		self.serial.close()


class ManchesterFlash(Flash):
	
	# Address of the start of the control block
	CONTROL_BLOCK = 0x4000
	
	# Number of boot table entries
	NUM_BOOTS = 16
	
	# Magic number for boot table entries
	BOOT_MAGIC_NUMBER = "CODE"
	
	# Flag meanings for the various bits in the flag boot table entry
	BOOT_FLAGS = {
		1<<19 : "Enable Data Cache",
		1<<18 : "Enable Instruction Cache",
		1<<17 : "Do-not Disable Watchdog",
		1<<16 : "Disable Reset Button",
		1<<9  : "Zero External RAM",
		1<<8  : "Zero Internal RAM",
		1<<4  : "Checksum ROM",
		1<<3  : "Start in RAM",
		1<<2  : "LEDs Enabled",
		1<<1  : "LCD Baclight Enabled",
		1<<0  : "Print LCD Message",
	}
	
	# Individually erasable sectors in the Flash memory
	ROM_SECTORS = [
		(0x000000, 0x004000),
		(0x004000, 0x006000),
		(0x006000, 0x008000),
		(0x008000, 0x010000),
		
		(0x010000, 0x020000),
		(0x020000, 0x030000),
		(0x030000, 0x040000),
		(0x040000, 0x050000),
		(0x050000, 0x060000),
		(0x060000, 0x070000),
		(0x070000, 0x080000),
		(0x080000, 0x090000),
		(0x090000, 0x0A0000),
		(0x0A0000, 0x0B0000),
		(0x0B0000, 0x0C0000),
		(0x0C0000, 0x0D0000),
		(0x0D0000, 0x0E0000),
		(0x0E0000, 0x0F0000),
		(0x0F0000, 0x100000),
		(0x100000, 0x110000),
		(0x110000, 0x120000),
		(0x120000, 0x130000),
		(0x130000, 0x140000),
		(0x140000, 0x150000),
		(0x150000, 0x160000),
		(0x160000, 0x170000),
		(0x170000, 0x180000),
		(0x180000, 0x190000),
		(0x190000, 0x1A0000),
		(0x1A0000, 0x1B0000),
		(0x1B0000, 0x1C0000),
		(0x1C0000, 0x1D0000),
		(0x1D0000, 0x1E0000),
		(0x1E0000, 0x1F0000),
		(0x1F0000, 0x200000),
	]
	
	
	def __init__(self, port = 0):
		Flash.__init__(self, port, baudrate = 115200,
		               timeout = 1.0, writeTimeout = 0.1)
	
	
	
	def get_boot_table(self):
		"""
		Get the boot table (and decode into fields)
		"""
		out = []
		for boot in range(ManchesterFlash.NUM_BOOTS):
			data = self.rom_read(ManchesterFlash.CONTROL_BLOCK + (boot * 0x100), 0x100)
			
			magic_number     =     data[0x00:0x04]
			flags            = b2i(data[0x04:0x08])
			ram_img_start    = b2i(data[0x08:0x0C])
			ram_img_length   = b2i(data[0x0C:0x10])
			rom_img_start    = b2i(data[0x10:0x14])
			rom_img_length   = b2i(data[0x14:0x18])
			rom_exec_offset  = b2i(data[0x18:0x1C])
			rom_exec_cpsr    = b2i(data[0x1C:0x20])
			spartan_start    = b2i(data[0x20:0x24])
			spartan_length   = b2i(data[0x24:0x28])
			virtex_start     = b2i(data[0x28:0x2C])
			virtex_length    = b2i(data[0x2C:0x30])
			lcd_msg, z, tail =     data[0x30:].rstrip("\xFF").partition("\0")
			
			if magic_number != ManchesterFlash.BOOT_MAGIC_NUMBER:
				out.append(None)
			else:
				out.append((
					flags,
					ram_img_start,   ram_img_length,
					rom_img_start,   rom_img_length,
					rom_exec_offset, rom_exec_cpsr,
					spartan_start,   spartan_length,
					virtex_start,    virtex_length,
					lcd_msg,         tail,
				))
		
		return out
	
	
	def get_memory_table(self, boot_table = None):
		"""
		Extract a table of memory entries from a boot table.  Returns a list of
		((start, end), name) tuples.
		"""
		if boot_table is None:
			boot_table = self.get_boot_table()
		
		ranges = [
			((ManchesterFlash.CONTROL_BLOCK,
			  ManchesterFlash.CONTROL_BLOCK + (0x100 * ManchesterFlash.NUM_BOOTS)),
			 "Boot Table"),
			((0x008000, 0x010000), "MMU Default Table"),
		]
		
		for boot_num, boot in enumerate(boot_table):
			if boot is None:
				continue
			(
				flags,
				ram_img_start,   ram_img_length,
				rom_img_start,   rom_img_length,
				rom_exec_offset, rom_exec_cpsr,
				spartan_start,   spartan_length,
				virtex_start,    virtex_length,
				lcd_msg,         tail
			) = boot
			
			if ram_img_length:
				ranges.append(((ram_img_start, ram_img_start+ram_img_length),
				               "Boot %d RAM Image"%boot_num))
			if rom_img_length:
				ranges.append(((rom_img_start, rom_img_start+rom_img_length),
				               "Boot %d ROM Image"%boot_num))
			if spartan_length:
				ranges.append(((spartan_start, spartan_start+spartan_length),
				               "Boot %d Spartan Image"%boot_num))
			if virtex_length:
				ranges.append(((virtex_start, virtex_start+virtex_length),
				               "Boot %d Virtex Image"%boot_num))
		
		return sorted(ranges, key = (lambda ((s,e), n): s),
		                      reverse = True)
	
	
	def get_pretty_memory_table(self, memory_table = None):
		"""
		Prettify a memory table.
		"""
		if memory_table is None:
			memory_table = self.get_memory_table()
		
		out = "ROM Allocation:\n"
		
		WIDTH = 30
		
		last_addr = ManchesterFlash.ROM_SECTORS[-1][1]
		for (start,end), name in memory_table:
			if end != last_addr:
				out += "  +" + "-"*WIDTH + "+\n"
				out += "  '" + " "*WIDTH + "' %06X\n"%(last_addr-1)
				out += "  ," + " "*WIDTH + ", %06X\n"%end
			
			size = "(%X bytes)"%(end-start)
			
			out += "  +"  + "-"*WIDTH            +  "+\n"
			out += "  |"  + " "*WIDTH            +  "| %06X\n"%(end-1)
			out += "  | " + name.center(WIDTH-2) + " |\n"
			out += "  | " + size.center(WIDTH-2) + " |\n"
			out += "  |"  + " "*WIDTH            +  "| %06X\n"%start
			
			last_addr = start
		
		if 0 != last_addr:
			out += "  +" + "-"*WIDTH + "+\n"
			out += "  '" + " "*WIDTH + "' %06X\n"%(last_addr-1)
			out += "  ," + " "*WIDTH + ", %06X\n"%0
		out += "  +" + "-"*WIDTH + "+\n"
		
		return out
	
	
	def get_pretty_boot_table(self, boot_table = None):
		"""
		Prettifys a boot table
		"""
		out = ""
		
		if boot_table is None:
			boot_table = self.get_boot_table()
		
		for boot_num, boot in enumerate(boot_table):
			if boot is None:
				continue
			(
				flags,
				ram_img_start,   ram_img_length,
				rom_img_start,   rom_img_length,
				rom_exec_offset, rom_exec_cpsr,
				spartan_start,   spartan_length,
				virtex_start,    virtex_length,
				lcd_msg,         tail
			) = boot
			
			
			flag_list = []
			for bit in sorted(ManchesterFlash.BOOT_FLAGS.keys()):
				flag = ManchesterFlash.BOOT_FLAGS[bit]
				if flags & bit:
					flag_list.append("%08X: %s"%(bit, flag))
			flag_list = "\n".join(flag_list)
			
			out += "Boot %d:\n"%boot_num
			if flag_list:
				out += "  Flags: " + ("\n"+" "*9).join(flag_list.split("\n")) + "\n"
			if ram_img_length:
				out += "  RAM Image: %08X - %08X (%X bytes)\n"%(ram_img_start,
				                                              ram_img_start+ram_img_length-1,
				                                              ram_img_length)
			if rom_img_length:
				out += "  ROM Image: %08X - %08X (%X bytes)\n"%(rom_img_start,
				                                              rom_img_start+rom_img_length-1,
				                                              rom_img_length)
			out += "  ROM Start Offset: %X (CPSR = %08X)\n"%(rom_exec_offset,
			                                                 rom_exec_cpsr)
			if spartan_length:
				out += "  Spartan Image: %08X - %08X (%X bytes)\n"%(spartan_start,
				                                                  spartan_start+spartan_length-1,
				                                                  spartan_length)
			if virtex_length:
				out += "  Virtex Image:  %08X - %08X (%X bytes)\n"%(virtex_start,
				                                                  virtex_start+virtex_length-1,
				                                                  virtex_length)
			if lcd_msg:
				out += "  LCD Message: %s\n"%(("\n"+" "*15).join(wrap(repr(lcd_msg), 65)))
			if tail:
				out += "  Tail: %s\n"%(("\n"+" "*8).join(wrap(repr(tail), 72)))
			out += "\n"
		
		return out.strip() + "\n"
	
	
	def check_erase(self, address, memory_table = None, boot_table = None):
		"""
		Return a tuple ((start, end), clobbered) where start and end are the start
		and end of the area to be erased and clobbered is a list of memory blocks
		which would be clobbered by an erase to the given block.
		"""
		
		for start,end in ManchesterFlash.ROM_SECTORS:
			if start <= address < end:
				break
			start,end = None,None
		
		if memory_table is None:
			memory_table = self.get_memory_table(boot_table)
		
		clobbered = []
		for ((m_start, m_end), name) in memory_table:
			if m_start <= start < m_end or m_start <= end < m_end:
				clobbered.append(((m_start, m_end), name))
		
		return ((start, end), clobbered)


if __name__=="__main__":
	b = ManchesterFlash("/dev/ttyUSB0")
	b.ping()
	print b.get_pretty_boot_table()
	print b.get_pretty_memory_table()
	print b.check_erase(0x4100)
