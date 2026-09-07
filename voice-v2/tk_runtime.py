"""Windows Tcl/Tk startup compatibility helper.

Some Python installations have a valid Tcl/Tk payload but fail to initialize its
filesystem layer before tkinter creates the first interpreter. Initializing one
short-lived Tcl interpreter with an explicit library path fixes that state.
"""

from __future__ import annotations

import ctypes
import os
import sys


def prepare_tk() -> None:
    if os.name != "nt":
        return

    tcl_dir = os.path.join(sys.base_prefix, "tcl", "tcl8.6")
    tcl_dll = os.path.join(sys.base_prefix, "DLLs", "tcl86t.dll")
    if not (os.path.isfile(os.path.join(tcl_dir, "init.tcl")) and os.path.isfile(tcl_dll)):
        return

    dll = ctypes.WinDLL(tcl_dll)
    pointer = ctypes.c_void_p
    dll.Tcl_FindExecutable.argtypes = [ctypes.c_char_p]
    dll.Tcl_CreateInterp.restype = pointer
    dll.Tcl_Eval.argtypes = [pointer, ctypes.c_char_p]
    dll.Tcl_Init.argtypes = [pointer]
    dll.Tcl_DeleteInterp.argtypes = [pointer]

    dll.Tcl_FindExecutable(sys.executable.encode("utf-8"))
    interp = dll.Tcl_CreateInterp()
    if not interp:
        return

    try:
        normalized = tcl_dir.replace("\\", "/")
        dll.Tcl_Eval(interp, f"set tcl_library {{{normalized}}}".encode("utf-8"))
        dll.Tcl_Init(interp)
    finally:
        dll.Tcl_DeleteInterp(interp)
