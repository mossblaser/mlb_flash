#!/usr/bin/env python

import sys
from textwrap import wrap

from flash import ManchesterFlash

COMMANDS = {
}

def do_help(flash, _):
	"""
	Print out documentation for each command.
	"""
	
	func_commands = {}
	
	for command, func in COMMANDS.iteritems():
		func_commands.setdefault(func, []).append(command)
	
	for func, commands in func_commands.iteritems():
		doc = func.__doc__.strip().split("\n")
		lines = []
		acc = ""
		for line in doc:
			line = line.strip()
			if line == "" and acc != "":
				lines.append(acc)
				acc = ""
			elif line != "":
				acc += " %s"%line
		if acc != "":
			lines.append(acc)
		
		print "%s"%(", ".join(commands))
		for line in lines:
			print "  %s\n"%("\n  ".join(wrap(line.strip())))
	
	return True

COMMANDS['h']    = do_help
COMMANDS['?']    = do_help
COMMANDS['help'] = do_help


def do_quit(flash, _):
	"""
	Quit the flash program.
	"""
	flash.close()
	return False

COMMANDS['q']    = do_quit
COMMANDS['quit'] = do_quit


def do_boot_table(flash, _):
	"""
	Show the contents of the boot table.
	"""
	print flash.get_pretty_boot_table()
	return True

COMMANDS['b']     = do_boot_table
COMMANDS['boot']  = do_boot_table


def do_rom_table(flash, _):
	"""
	Show the contents of ROM (according to the boot table).
	"""
	print flash.get_pretty_memory_table()
	return True

COMMANDS['rom']  = do_rom_table


def do_erase(flash, args):
	"""
	Erase a block of ROM at the given address. Will prompt for confirmation
	unless -f is given.
	"""
	force = False
	
	if "-f" in args:
		args.remove("-f")
		force = True
	
	addr = int(args[0], 16)

	if not force:
		print "Checking memory map..."
		(start, end), clobbered = flash.check_erase(addr)
		print "Block %06X - %06X (%X bytes) will be erased."%(start, end-1, end-start)
		if clobbered:
			print "This block contains:"
			for (start,end), name in clobbered:
				print "  %06X - %06X %s (%X bytes)"%(start, end-1, name, end-start)
		if raw_input("Are you sure? [y/N] ").strip().lower() not in "y yes".split():
			# No confirm
			print "Cancelled."
			return True
	
	(start,end),_ = flash.check_erase(addr, [])
	print "Erasing %06X - %06X (%X bytes)..."%(start,end-1, end-start)
	flash.erase(addr)
	
	return True

COMMANDS['e']      = do_erase
COMMANDS['erase']  = do_erase



def do_read(flash, args):
	"""
	Read an image from the memory. If the filename is -, display onscreen.
	
	read filename addr length
	"""
	force = False
	
	filename = args[0]
	addr     = int(args[1], 16)
	length   = int(args[2], 16)

	from sys import stdout
	if filename == "-":
		# Write to stdout
		for block in flash.rom_read_(addr, length):
			stdout.write(repr(block)[1:-1])
			stdout.flush()
		print ""
	else:
		# Write to file
		f = open(filename, "w")
		stdout.write("Flash ")
		stdout.flush()
		
		got = 0
		printed = 0
		aaaahh = "a"*40 + "h"*33 + "!"
		for block in flash.rom_read_(addr, length):
			got += len(block)
			to_print = (len(aaaahh) * got) / length
			stdout.write(aaaahh[printed:to_print])
			stdout.flush()
			printed = to_print
		f.close()
		print ""
	
	return True

COMMANDS['r']    = do_read
COMMANDS['read'] = do_read


def pretty_write(flash, addr, data):
	from sys import stdout
	stdout.write("Flash ")
	stdout.flush()
	length = len(data)
	
	sent = 0
	printed = 0
	aaaahh = "a"*40 + "h"*33 + "!"
	for block_length in flash.rom_write_(addr, data):
		sent += block_length
		to_print = (len(aaaahh) * sent) / length
		stdout.write(aaaahh[printed:to_print])
		stdout.flush()
		printed = to_print
	print ""


def do_write(flash, args):
	"""
	Write an image to the memory.
	
	write filename addr length
	"""
	force = False
	
	filename = args[0]
	addr     = int(args[1], 16)
	length   = int(args[2], 16)

	# Write to file
	f = open(filename, "r")
	data = f.read(length)
	f.close()
	
	data = data.ljust(length, "\xFF")
	
	pretty_write(flash, addr, data)
	
	return True

COMMANDS['w']     = do_write
COMMANDS['write'] = do_write


def do_write_elf(flash, args):
	"""
	Write the PROGBITS sections of an ELF file to the addresses of the ROM
	specified.
	
	elf [elffile]
	"""
	force = False
	
	filename = args[0]

	# Write to file
	data_sections = {}
	f = open(filename, "rb")
	for section in ELFFile(f).iter_sections():
		if section["sh_type"] == "SHT_PROGBITS":
			data_sections[section["sh_addr"]] = section.data()
	f.close()
	
	for addr, data in data_sections.iter_items():
		print "Writing section at %08X"%addr
		pretty_write(flash, addr, data)
	
	return True

COMMANDS['e']         = do_write_elf
COMMANDS['elf']       = do_write_elf
COMMANDS['write_elf'] = do_write_elf



def do_comand(flash):
	raw_command = raw_input("Flash > ")
	tokens = filter(None, raw_command.split())
	command = tokens[0]
	args    = tokens[1:]
	
	if command in COMMANDS:
		try:
			return COMMANDS[command](flash, args)
		except Exception, e:
			print e
			return True
	else:
		print "Command %s not found"%repr(command)
		return True



if __name__ == "__main__":
	flash = ManchesterFlash(*sys.argv[1:])
	
	while do_comand(flash):
		pass
