import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk
from gui.main_window import MainWindow


def main():
    ctk.set_appearance_mode("System")
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
