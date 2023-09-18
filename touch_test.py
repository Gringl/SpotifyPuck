#!/usr/bin/env python3
import os
import pygame
import time
import math
from hyperpixel2r import Touch
import spotipy
import sys
import requests
from spotipy.oauth2 import SpotifyOAuth
from pygame.locals import *

SPOTIPY_CLIENT_ID = '3e64a448ffda4cb6ad51e8f0da677680'
SPOTIPY_CLIENT_SECRET = os.environ['SPOTIPY_CLIENT_SECRET']
SPOTIPY_REDIRECT_URI = 'https://localhost:8080'
if not SPOTIPY_CLIENT_SECRET:
    raise ValueError("SPOTIPY_CLIENT_SECRET is not set in the environment variables.")
# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope="user-modify-playback-state user-read-playback-state",
                                               open_browser=False))

class Hyperpixel2r:
    screen = None

    def __init__(self):
        self._init_display()

        self.screen.fill((0, 0, 0))
        self._updatefb()

        self._step = 0
        self._steps = [
            (255, 0, 0, 240, 100),  # Top
            (0, 255, 0, 240, 380),  # Bottom
            (255, 0, 0, 100, 240),  # Left
            (0, 255, 0, 380, 240),  # Right
            (0, 0, 255, 240, 240),  # Middle
        ]
        self._touched = False

    def _init_display(self):

        self._rawfb = False
        # Based on "Python GUI in Linux frame buffer"
        # http://www.karoltomala.com/blog/?p=679
        pygame.init()
        DISPLAY = os.getenv("DISPLAY")
        if DISPLAY:
            print("Display: {0}".format(DISPLAY))

        if os.getenv('SDL_VIDEODRIVER'):
            print("Using driver specified by SDL_VIDEODRIVER: {}".format(os.getenv('SDL_VIDEODRIVER')))
            pygame.init()
            pygame.display.init()
            pygame.font.init()
            size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
            if size == (480, 480): # Fix for 480x480 mode offset
                size = (640, 480)
            self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.NOFRAME | pygame.HWSURFACE)
            return

        else:
            # Iterate through drivers and attempt to init/set_mode
            for driver in ['rpi', 'kmsdrm', 'fbcon', 'directfb', 'svgalib']:
                os.putenv('SDL_VIDEODRIVER', driver)
                try:
                    pygame.display.init()
                    size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
                    if size == (480, 480):  # Fix for 480x480 mode offset
                        size = (640, 480)
                    self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.NOFRAME | pygame.HWSURFACE)
                    print("Using driver: {0}, Framebuffer size: {1:d} x {2:d}".format(driver, *size))
                    return
                except pygame.error as e:
                    print('Driver "{0}" failed: {1}'.format(driver, e))
                    continue
                break

        print("All SDL drivers failed, falling back to raw framebuffer access.")
        self._rawfb = True
        os.putenv('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()  # Need to init for .convert() to work
        self.screen = pygame.Surface((480, 480))

    def __del__(self):
        "Destructor to make sure pygame shuts down, etc."

    def _updatefb(self):
        if not self._rawfb:
            pygame.display.update()
            return

        fbdev = os.getenv('SDL_FBDEV', '/dev/fb0')
        with open(fbdev, 'wb') as fb:
            fb.write(self.screen.convert(16, 0).get_buffer())

    def touch(self, x, y, state):
        if state:
            # Define the coordinates for the Play/Pause button
            button_x, button_y = 240, 240
            distance = math.sqrt((button_x - x)**2 + (button_y - y)**2)
            if distance < 90:
                self._touched = True
                self.toggle_playback()

    def toggle_playback(self):
        # Toggle Spotify playback
        playback = sp.current_playback()
        if playback and playback['is_playing']:
            sp.pause_playback()
        else:
            sp.start_playback()

    def display_button(self):
        # Display the Play/Pause button
        pygame.draw.circle(self.screen, (0, 255, 0), (240, 240), 90)
        self._updatefb()

    def display_song_info(self):
        # Fetch current song information
        playback = sp.current_playback()
        if playback and playback['item']:
            song_name = playback['item']['name']
            artist_name = playback['item']['artists'][0]['name']
            album_cover_url = playback['item']['album']['images'][0]['url']  # Get the URL of the album cover

            # Download the album cover
            response = requests.get(album_cover_url)
            album_cover = pygame.image.load(io.BytesIO(response.content))

            # Clear the screen
            self.screen.fill((0, 0, 0))

            # Set up the font and colors
            font = pygame.font.Font(None, 36)
            text_color = (255, 255, 255)

            # Render song name and artist
            song_surface = font.render(song_name, True, text_color)
            artist_surface = font.render(artist_name, True, text_color)

            # Position the text lower and centered
            song_rect = song_surface.get_rect(center=(240, 320))
            artist_rect = artist_surface.get_rect(center=(240, 360))

            # Draw the text on the screen
            self.screen.blit(song_surface, song_rect)
            self.screen.blit(artist_surface, artist_rect)

            # Display the album cover in the middle and make it spin
            # Note: This is a basic implementation. You might need to adjust for the desired effect.
            angle = 0
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                rotated_cover = pygame.transform.rotate(album_cover, angle)
                rect = rotated_cover.get_rect(center=(240, 240))
                self.screen.blit(rotated_cover, rect.topleft)
                pygame.display.flip()
                angle += 1  # Adjust this value for faster or slower rotation
                time.sleep(0.01)  # Adjust this value for smoother or choppier rotation

            # Update the display
            self._updatefb()
display = Hyperpixel2r()
touch = Touch()

@touch.on_touch
def handle_touch(touch_id, x, y, state):
    display.touch(x, y, state)

display.display_button()
display.display_song_info()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    time.sleep(0.1)
