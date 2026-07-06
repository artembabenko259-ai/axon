"""AXON Dart: Unified decompiler engine for C/C++, Java, and C#/.NET."""

from __future__ import annotations

import os
import struct
import subprocess
from pathlib import Path
import re

# Java Bytecode Opcode Mapping (Subset for clean C-like pseudo-code translation)
JVM_OPCODES = {
    0x00: ("nop", 0), 0x01: ("aconst_null", 0),
    0x02: ("iconst_m1", 0), 0x03: ("iconst_0", 0), 0x04: ("iconst_1", 0),
    0x05: ("iconst_2", 0), 0x06: ("iconst_3", 0), 0x07: ("iconst_4", 0),
    0x08: ("iconst_5", 0), 0x09: ("lconst_0", 0), 0x0a: ("lconst_1", 0),
    0x10: ("bipush", 1), 0x11: ("sipush", 2), 0x12: ("ldc", 1), 0x13: ("ldc_w", 2),
    0x15: ("iload", 1), 0x19: ("aload", 1),
    0x1a: ("iload_0", 0), 0x1b: ("iload_1", 0), 0x1c: ("iload_2", 0), 0x1d: ("iload_3", 0),
    0x2a: ("aload_0", 0), 0x2b: ("aload_1", 0), 0x2c: ("aload_2", 0), 0x2d: ("aload_3", 0),
    0x36: ("istore", 1), 0x3a: ("astore", 1),
    0x3b: ("istore_0", 0), 0x3c: ("istore_1", 0), 0x3d: ("istore_2", 0), 0x3e: ("istore_3", 0),
    0x4b: ("astore_0", 0), 0x4c: ("astore_1", 0), 0x4d: ("astore_2", 0), 0x4e: ("astore_3", 0),
    0x60: ("iadd", 0), 0x64: ("isub", 0), 0x68: ("imul", 0), 0x6c: ("idiv", 0),
    0x84: ("iinc", 2),
    0x99: ("ifeq", 2), 0x9a: ("ifne", 2), 0x9b: ("iflt", 2), 0x9c: ("ifge", 2),
    0x9d: ("ifgt", 2), 0x9e: ("ifle", 2), 0xa7: ("goto", 2),
    0xac: ("ireturn", 0), 0xb0: ("areturn", 0), 0xb1: ("return", 0),
    0xb2: ("getstatic", 2), 0xb3: ("putstatic", 2), 0xb4: ("getfield", 2), 0xb5: ("putfield", 2),
    0xb6: ("invokevirtual", 2), 0xb7: ("invokespecial", 2), 0xb8: ("invokestatic", 2),
    0xbb: ("new", 2),
}

def decompile_class_file(file_path: Path) -> str:
    """Parses a Java .class file and returns pseudo-Java/C decompiled output."""
    try:
        data = file_path.read_bytes()
        if len(data) < 8:
            return "Error: Invalid class file (too short)."
            
        magic = struct.unpack(">I", data[0:4])[0]
        if magic != 0xCAFEBABE:
            return "Error: Invalid JVM magic header (expected 0xCAFEBABE)."
            
        minor, major = struct.unpack(">HH", data[4:8])
        
        # Simple Constant Pool parsing
        pool_count = struct.unpack(">H", data[8:10])[0]
        offset = 10
        cp = {}
        
        i = 1
        while i < pool_count:
            tag = data[offset]
            if tag == 1: # UTF-8 String
                length = struct.unpack(">H", data[offset+1:offset+3])[0]
                val = data[offset+3:offset+3+length].decode("utf-8", errors="ignore")
                cp[i] = ("Utf8", val)
                offset += 3 + length
            elif tag == 7: # Class info
                name_idx = struct.unpack(">H", data[offset+1:offset+3])[0]
                cp[i] = ("Class", name_idx)
                offset += 3
            elif tag == 8: # String info
                str_idx = struct.unpack(">H", data[offset+1:offset+3])[0]
                cp[i] = ("String", str_idx)
                offset += 3
            elif tag in (9, 10, 11): # Ref fields/methods
                class_idx, nt_idx = struct.unpack(">HH", data[offset+1:offset+5])
                cp[i] = ("Ref", class_idx, nt_idx)
                offset += 5
            elif tag == 12: # Name and Type
                name_idx, type_idx = struct.unpack(">HH", data[offset+1:offset+5])
                cp[i] = ("NameAndType", name_idx, type_idx)
                offset += 5
            elif tag in (3, 4): # Integer / Float
                offset += 5
            elif tag in (5, 6): # Long / Double
                offset += 9
                i += 1 # Double/Long take two entries
            elif tag in (15, 16, 18): # MethodHandle/MethodType/InvokeDynamic
                offset += 4 if tag != 15 else 5
            else:
                break
            i += 1

        def get_cp_string(idx: int) -> str:
            if idx not in cp:
                return f"#{idx}"
            item = cp[idx]
            if item[0] == "Utf8":
                return item[1]
            if item[0] == "Class":
                return get_cp_string(item[1])
            if item[0] == "String":
                return get_cp_string(item[1])
            if item[0] == "NameAndType":
                return f"{get_cp_string(item[1])}:{get_cp_string(item[2])}"
            if item[0] == "Ref":
                return f"{get_cp_string(item[1])}.{get_cp_string(item[2])}"
            return str(item)

        # Skip access flags, this class, super class, interfaces
        offset += 6
        interfaces_count = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2 + 2 * interfaces_count
        
        # Skip fields
        fields_count = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        for _ in range(fields_count):
            attr_count = struct.unpack(">H", data[offset+6:offset+8])[0]
            offset += 8
            for _ in range(attr_count):
                attr_len = struct.unpack(">I", data[offset+2:offset+6])[0]
                offset += 6 + attr_len
                
        # Parse methods
        methods_count = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        
        decompiled = []
        decompiled.append(f"// JVM Class version: {major}.{minor}")
        decompiled.append("class JavaClassTarget {")
        
        for _ in range(methods_count):
            access_flags, name_idx, desc_idx, attr_count = struct.unpack(">HHHH", data[offset:offset+8])
            method_name = get_cp_string(name_idx)
            method_desc = get_cp_string(desc_idx)
            offset += 8
            
            code_bytes = b""
            for _ in range(attr_count):
                attr_name_idx = struct.unpack(">H", data[offset:offset+2])[0]
                attr_len = struct.unpack(">I", data[offset+2:offset+6])[0]
                attr_name = get_cp_string(attr_name_idx)
                
                if attr_name == "Code":
                    code_len = struct.unpack(">I", data[offset+10:offset+14])[0]
                    code_bytes = data[offset+14:offset+14+code_len]
                offset += 6 + attr_len
            
            decompiled.append(f"\n    // Method Signature: {method_name}{method_desc}")
            decompiled.append(f"    public void {method_name}() {{")
            
            pc = 0
            while pc < len(code_bytes):
                opcode = code_bytes[pc]
                if opcode in JVM_OPCODES:
                    name, args_len = JVM_OPCODES[opcode]
                    args_bytes = code_bytes[pc+1 : pc+1+args_len]
                    
                    args_str = ""
                    if args_len == 1:
                        args_str = str(args_bytes[0])
                    elif args_len == 2:
                        val = struct.unpack(">H", args_bytes)[0]
                        if name in ("getstatic", "invokevirtual", "invokespecial", "invokestatic", "new", "getfield"):
                            args_str = get_cp_string(val)
                        else:
                            args_str = str(val)
                            
                    decompiled.append(f"        {name} {args_str};")
                    pc += 1 + args_len
                else:
                    decompiled.append(f"        bytecode: 0x{opcode:02x};")
                    pc += 1
            decompiled.append("    }")
            
        decompiled.append("}")
        return "\n".join(decompiled)
    except Exception as exc:
        return f"Error parsing Java class: {exc}"


def decompile_csharp_file(file_path: Path) -> str:
    """Parses .NET assembly metadata tables and displays C# class structure/IL signatures."""
    try:
        res = subprocess.run(["ildasm", "/text", str(file_path)], capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout
            
        data = file_path.read_bytes()
        if len(data) < 64:
            return "Error: Invalid PE / C# assembly file."
            
        idx = data.find(b"BSJB")
        if idx == -1:
            return "Error: File is not a C#/.NET assembly (missing CLR metadata header)."
            
        version_len = struct.unpack("<I", data[idx+12:idx+16])[0]
        version = data[idx+16:idx+16+version_len].decode("utf-8", errors="ignore").strip("\x00")
        
        strings = []
        for match in re.finditer(b"[\x20-\x7E]{4,50}\x00", data):
            s = match.group(0).decode("ascii", errors="ignore").strip("\x00")
            if s and not s.startswith(".") and not s.endswith(".dll"):
                if s not in ("mscorlib", "System", "RuntimeCompatibilityAttribute", "CompilerGeneratedAttribute"):
                    strings.append(s)
                    
        decompiled = [
            f"// .NET CLR Version: {version}",
            "// C# Pseudo-Decompilation (Signature Extract)",
            "namespace TargetAssembly {",
        ]
        
        classes = {}
        curr_class = "GlobalClass"
        for s in strings:
            if s.istitle() and "_" not in s:
                curr_class = s
                if curr_class not in classes:
                    classes[curr_class] = []
            elif s.isidentifier():
                if curr_class in classes and s not in classes[curr_class]:
                    classes[curr_class].append(s)
                    
        for cls, methods in classes.items():
            decompiled.append(f"    public class {cls} {{")
            for m in methods:
                decompiled.append(f"        public void {m}();")
            decompiled.append("    }")
        decompiled.append("}")
        
        return "\n".join(decompiled)
    except Exception as exc:
        return f"Error parsing C# Assembly: {exc}"


def decompile_native_file(file_path: Path, symbol_name: str | None = None) -> str:
    """Uses Radare2 (r2) or objdump to decompile native C/C++ assemblies."""
    try:
        r2_cmd = ["r2", "-q", "-c", "aa; afl"]
        if symbol_name:
            r2_cmd = ["r2", "-q", "-c", f"aa; pdf @ {symbol_name}"]
        r2_cmd.append(str(file_path))
        
        res = subprocess.run(r2_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout
            
        obj_cmd = ["objdump", "-d"]
        if symbol_name:
            obj_cmd += ["-j", ".text"]
        obj_cmd.append(str(file_path))
        
        res = subprocess.run(obj_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout
            
        data = file_path.read_bytes()
        strings = []
        for match in re.finditer(b"[\x20-\x7E]{5,80}\x00", data):
            s = match.group(0).decode("ascii", errors="ignore").strip("\x00")
            if s:
                strings.append(s)
                
        return "// Native C/C++ target (disassembler unavailable)\n// Extracted strings:\n" + "\n".join(strings[:50])
    except Exception as exc:
        return f"Error disassembling native file: {exc}"


def decompile_file(file_path_str: str, symbol_name: str | None = None) -> str:
    """Decompile entry point. Dispatches to JVM, CLR, or Native handlers."""
    p = Path(file_path_str)
    if not p.is_file():
        return f"Error: File not found: {file_path_str}"
        
    ext = p.suffix.lower()
    if ext in (".class", ".jar"):
        return decompile_class_file(p)
    elif ext in (".exe", ".dll") and p.read_bytes().find(b"BSJB") != -1:
        return decompile_csharp_file(p)
    else:
        return decompile_native_file(p, symbol_name)
