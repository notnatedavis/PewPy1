#   src/workers/overlay.py
#   Overlay worker (passive)

# ----- Imports ----- #
import os
import threading
import time
import logging
from typing import Dict, Any, Tuple
from .function_worker import BaseWorker
try :
    import pygame
    import pygame.gfxdraw
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logging.warning("pygame not available - overlay disabled")
try :
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError :
    WIN32_AVAILABLE = False

# ----- Main Class ----- #
class Overlay(BaseWorker) :
    def __init__(self, 
                 position: Tuple[int, int] = (0, 0),
                 size: Tuple[int, int] = (300, 200),
                 opacity: int = 180) -> None:
        super().__init__(name="Overlay")
        self.position = position
        self.size = size
        self.opacity = opacity
        self.screen = None
        self.clock = None
        self.font = None
        self.display_data: Dict[str, Any] = {}
        self._data_lock = threading.RLock()
        self._initialized = False
        logging.info(f"Overlay initialized: size={size}, opacity={opacity}")
    
    def _work_cycle(self) -> None :
        if not PYGAME_AVAILABLE :
            return
        if not self._initialized :
            self._initialize_overlay()
            self._initialized = True
        self._handle_events()
        self._render_frame()
        if self.clock :
            self.clock.tick(60)
    
    def _initialize_overlay(self) -> None :
        try :
            pygame.init()
            self.screen = pygame.display.set_mode(self.size, pygame.NOFRAME)
            self.screen.set_alpha(self.opacity)
            # Position window (platform-specific)
            if hasattr(pygame, '_sdl2') :
                window = pygame.display.get_window()
                window.position = self.position
            else :
                os.environ['SDL_VIDEO_WINDOW_POS'] = f"{self.position[0]},{self.position[1]}"
                self.screen = pygame.display.set_mode(self.size, pygame.NOFRAME)
            if WIN32_AVAILABLE :
                self._setup_window_properties()
            pygame.display.set_caption("PewPy Overlay")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont('Arial', 16)
            logging.info("Overlay window initialized")
        except Exception as e :
            logging.error(f"Overlay init failed: {e}")
            raise
    
    def _setup_window_properties(self) -> None :
        try :
            hwnd = pygame.display.get_wm_info()["window"]
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
        except Exception as e :
            logging.warning(f"Window properties setup failed: {e}")
    
    def _handle_events(self) -> None :
        for event in pygame.event.get() :
            if event.type == pygame.QUIT :
                self.stop()  # but we don't have stop method; we need to signal? For now, ignore.
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE :
                # How to stop? We could set a flag, but BaseWorker doesn't have stop_event.
                # We'll assume manager will handle shutdown.
                pass
    
    def _render_frame(self) -> None :
        self.screen.fill((0,0,0,0))
        self._render_background()
        self._render_content()
        pygame.display.flip()
    
    def _render_background(self) -> None :
        s = pygame.Surface(self.size, pygame.SRCALPHA)
        s.fill((184,178,181,255))
        self.screen.blit(s, (0,0))
        pygame.draw.rect(self.screen, (255,255,255,100),
                         pygame.Rect(0,0,self.size[0],self.size[1]), 1)
    
    def _render_content(self) -> None :
        if not self.font :
            return
        with self._data_lock :
            data = self.display_data.copy()
        y = 10
        title = self.font.render("PewPy Overlay", True, (255,255,255))
        self.screen.blit(title, (10, y))
        y += 25
        pygame.draw.line(self.screen, (255,255,255,100), (10,y), (self.size[0]-10,y), 1)
        y += 10
        if not data :
            data = {"Status": "Running", "FPS": "60"}
        for k, v in data.items() :
            text = f"{k}: {v}"
            surf = self.font.render(text, True, (255,255,255))
            self.screen.blit(surf, (10, y))
            y += 20
    
    def update_data(self, new_data: Dict[str, Any]) -> None :
        with self._data_lock :
            self.display_data.update(new_data)
    
    def clear_data(self) -> None : 
        with self._data_lock :
            self.display_data.clear()
    
    def _cleanup(self) -> None :
        if pygame.get_init() :
            pygame.quit()
        self._initialized = False
        logging.debug("Overlay cleaned up")