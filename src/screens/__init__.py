# src/screens/__init__.py
# Explicitly export screen functions to prevent import issues

from src.screens.home_screen import home_screen
from src.screens.teacher_screen import teacher_screen
from src.screens.student_screen import student_screen

__all__ = ["home_screen", "teacher_screen", "student_screen"]