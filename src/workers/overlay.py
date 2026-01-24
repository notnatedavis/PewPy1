#   src/workers/overlay.py
#   Overlay functionality worker - Fixed method name mismatch

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
except ImportError :
    PYGAME_AVAILABLE = False
    logging.warning("pygame not available - overlay disabled")
try :
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError :
    WIN32_AVAILABLE = False

class Overlay(BaseWorker) :
    # Transparent overlay display for information
    
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
        # main overlay rendering loop
        if not PYGAME_AVAILABLE :
            logging.error("Overlay requires pygame")
            self.stop()
            return
        
        # initialize on first cycle
        if not self._initialized :
            self._initialize_overlay()
            self._initialized = True
        
        # handle events
        self._handle_events()
        
        # render frame
        self._render_frame()
        
        # control frame rate
        if self.clock :
            self.clock.tick(60)
    
    def _initialize_overlay(self) -> None :
        # initialize pygame overlay
        if not PYGAME_AVAILABLE :
            return
        
        try :
            pygame.init()
            self.screen = pygame.display.set_mode(self.size, pygame.NOFRAME)
            self.screen.set_alpha(self.opacity)
            
            # position window
            try :
                if hasattr(pygame, '_sdl2') :
                    window = pygame.display.get_window()
                    window.position = self.position
                else :
                    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{self.position[0]},{self.position[1]}"
                    self.screen = pygame.display.set_mode(self.size, pygame.NOFRAME)
            except Exception as e :
                logging.warning(f"Window positioning failed: {e}")
            
            # windows-specific properties
            if WIN32_AVAILABLE :
                self._setup_window_properties()
            
            pygame.display.set_caption("PewPy Overlay")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont('Arial', 16)
            
            logging.info("Overlay window initialized")
            
        except Exception as e :
            logging.error(f"Failed to initialize overlay: {e}")
            raise
    
    def _setup_window_properties(self) -> None :
        # setup window properties (Windows only)
        if not WIN32_AVAILABLE :
            return
        
        try :
            hwnd = pygame.display.get_wm_info()["window"]
            
            # always on top
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 
                                0, 0, 0, 0,
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            
            # transparent and click-through
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            
        except Exception as e :
            logging.warning(f"Window properties setup failed: {e}")
    
    def _handle_events(self) -> None :
        # Handle pygame events
        if not PYGAME_AVAILABLE or not self.screen :
            return
        
        for event in pygame.event.get() :
            if event.type == pygame.QUIT:
                self.stop()
            elif event.type == pygame.KEYDOWN :
                if event.key == pygame.K_ESCAPE :
                    self.stop()
    
    def _render_frame(self) -> None :
        # render one frame
        if not self.screen or not PYGAME_AVAILABLE :
            return
        
        # clear with transparent background
        self.screen.fill((0, 0, 0, 0))
        
        # draw elements
        self._render_background()
        self._render_content()
        
        pygame.display.flip()
    
    def _render_background(self) -> None :
        # render background
        if not self.screen :
            return
        
        s = pygame.Surface(self.size, pygame.SRCALPHA)
        s.fill((184, 178, 181, 255))
        self.screen.blit(s, (0, 0))
        
        # border
        pygame.draw.rect(self.screen, 
                        (255, 255, 255, 100),
                        pygame.Rect(0, 0, self.size[0], self.size[1]), 
                        1)
    
    def _render_content(self) -> None :
        # render overlay content
        if not self.font :
            return
        
        with self._data_lock :
            data = self.display_data.copy()
        
        y_offset = 10
        line_height = 20
        
        # title
        title = self.font.render("PewPy Overlay", True, (255, 255, 255))
        self.screen.blit(title, (10, y_offset))
        y_offset += line_height + 5
        
        # separator
        pygame.draw.line(self.screen, 
                        (255, 255, 255, 100),
                        (10, y_offset), 
                        (self.size[0]-10, y_offset), 
                        1)
        y_offset += 10
        
        # data (show default if empty)
        if not data :
            data = {"Status": "Running", "FPS": "60"}
        
        for key, value in data.items() :
            text = f"{key}: {value}"
            surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (10, y_offset))
            y_offset += line_height
    
    def update_data(self, new_data: Dict[str, Any]) -> None :
        # update overlay data
        with self._data_lock :
            self.display_data.update(new_data)
    
    def clear_data(self) -> None :
        # clear overlay data
        with self._data_lock :
            self.display_data.clear()
    
    def _cleanup(self) -> None :
        # cleanup resources
        if pygame.get_init() :
            pygame.quit()
        self._initialized = False
        logging.debug("Overlay cleanup completed")