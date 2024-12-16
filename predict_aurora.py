import requests
import musx.frac as fra
from braillestuff import makebraille 
import subprocess
import mido
import socket
import time
from music21 import converter, braille, environment
from music21.braille import translate
import io
import musx.paint as pnt

import rtmidi
from helpers import kp_solar, geteflux, gw_to_rayleighs, calculate_variance, find_path_of_most_variance
import pretty_midi
from musx import playfile, rescale
import math as m
import matplotlib.pyplot as plt
import scipy.io.wavfile as wavfile
import musx
import math
import statistics
import heapq
import musx.envs as env
from random import randint
from musx import spectral as spect
from musx import Score, Seq, MidiFile, Interval, Note, Pitch, rhythm, gens
from musx.midi.gm import TubularBells, Trumpet, Timpani, Cowbell, Xylophone, Vibraphone, Glockenspiel, Celesta, Harpsichord, MusicBox, Dulcimer
from musx import mxml
from musx.mxml import Notation
import random
import xml.etree.ElementTree as ET
from musx.mxml.notation import Notation
from musx.mxml.part import Part
from musx.mxml.measure import Measure
from musx.mxml.voice import Voice
from musx import Pitch
import musx.tools as mtool
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
 
import json
from flask_cors import CORS
from functools import lru_cache
 
import os
app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)

hpi_url = "https://services.swpc.noaa.gov/text/aurora-nowcast-hemi-power.txt"
aurora_url = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"

@lru_cache(maxsize=32)
def fetch_text_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None
@lru_cache(maxsize=32)
def fetch_json_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None

def parse_hpi_data(data):
    lines = data.strip().split('\n')
    n = []
    s = []
    timestamps = {}
    #number of divs determines midi file duration
    divs = int(len(lines) / 4)
    trak = 0
    for line in lines:
        if line.startswith('#'):
            continue
        parts = line.split()
        times = parts[0][-5:]
        
        if trak % divs == 0:
            timestamps[int(times[0:2])] = [float(parts[-2]), float(parts[-1])]
            n.append(float(parts[-2]))
            s.append(float(parts[-1]))
        trak += 1
    
    return n, s, timestamps
def get_aurora_intensity_for_location(aurora_data, latitude, longitude):
    for feature in aurora_data['coordinates']:
        if feature[1] == latitude and feature[0] == longitude:
            return feature[2]
    return None
def getwavelength(lat, long):
    outlook_url = "https://services.swpc.noaa.gov/text/27-day-outlook.txt"
    kp_value, solar_ind = kp_solar(outlook_url)
  
    indices_url = "https://services.swpc.noaa.gov/text/current-space-weather-indices.txt"
    electron_flux = geteflux(indices_url)
   
    latf = abs(lat / 90)
    longf = abs((long + 180) / 360)
    # print(lat, long, latf, longf)
   #constants
    sfcon = 1.5
    kpindcon = 10
    eflxcon = 2e-6
    return (sfcon*solar_ind + kpindcon*kp_value + eflxcon*electron_flux) * (latf + 1) / (longf + 1)
#helper that takes a light of gigawatt indexes for either hemisphere and a given aurora wavelength to return a list of rayleighs
def planck(wavelength_nm, gws, efficiency=0.01):
    h = 6.626e-34  # Planck's constant in Joules * seconds
    c = 3e8  # Speed of light in meters/second
    # Convert wavelength from nanometers to meters
    wavelength_m = wavelength_nm * 1e-9
    # Calculate the energy of one photon (E = hc / λ)
    photon_energy_j = (h * c) / (wavelength_m+1)
    rayleighs_list = []
    
    for power_gw in gws:
        # Convert power from gigawatts to watts
        power_w = power_gw * 1e9
        
        # Calculate the visible power based on efficiency
        visible_power_w = power_w * efficiency
        
        # Calculate the number of photons emitted per second
        photons_per_second = visible_power_w / (photon_energy_j+1)
        
        # Convert photons per second to Rayleighs
        rayleighs = photons_per_second / 1e6
        
        # Append the result to the list
        rayleighs_list.append(rayleighs)
    
    return rayleighs_list

def predict_aurora_color(intensity, hemi_power):
    adji = [(intensity * (i / 50)) for i in hemi_power]
    adjcol = ["Red" if i >= 6.5 else "Yellow" if i >= 6 else "Green" if i >= 1 else "Blue" if i >= 0.5 else "Purple" for i in adji]
    return adjcol
@app.route('/generate_sound', methods=['POST'])
def generate_sound():
    print("Beginning sonification")
    data = request.json
    direction = data.get('direction')
    print(direction)
    if direction not in ['north', 'south']:
        return jsonify({"error": "Invalid direction"}), 400
    try:
        sonify_stuff(direction)
        print("Outside MIDI sending function")
        makebraille()
        print("did i make a braille?")
        file_path = os.path.join(app.static_folder, 'brlxml.brl')
        if not os.path.exists(file_path):
            return jsonify({"error": "Braiile file not found"}), 404
        # Ensure the file path is correct
        midi_file_path = '/Users/simoncooper/Desktop/Light Sonification/asonifiy.mid'
        if not os.path.exists(midi_file_path):
            return jsonify({"error": "MIDI file not found"}), 404

        return send_file(midi_file_path, as_attachment=True)
    except Exception as e:
        print(f"Error during sound generation: {e}")
        return jsonify({"error": "An error occurred during sound generation."}), 500
def wv_to_col(wv):
    #this got halved
    if wv <= 130:
        return "Purple"
    if wv <= 260:
        return "Blue"
    if wv < 290:
        return "Teal"
    if wv <= 330:
        return "Green"
    if wv <= 345:
        return "Yellow"
    if wv <= 370:
        return "Orange"
    
    else:
        return "Red"
def sonify_stuff(direction):
    hpi_data = fetch_text_data(hpi_url)
    northern_hemi_power, southern_hemi_power, timestamps = parse_hpi_data(hpi_data)
    aurora_data = fetch_json_data(aurora_url)
    no_zeros = [entry for entry in aurora_data['coordinates'] if entry[2] != 0]
    north = [n for n in no_zeros if float(n[1]) >= 0]
    south = [n for n in no_zeros if float(n[1]) < 0]
    nlats = [n[1] for n in north]
    slats = [s[1] for s in south]

    microdivs = 7
    instrumentation = {0: Harpsichord,  1: Vibraphone, 2: MusicBox , 3:Celesta , 4: Dulcimer, 5: TubularBells, 6: Glockenspiel}
    iinst = {"Purple": 0, "Blue": 1, "Teal": 2, "Green": 3, "Yellow": 4, "Orange":5, "Red":6}
  
    track0 = MidiFile.metatrack(tempo=200, timesig=[4, 4], ins=instrumentation, microdivs=microdivs)

    score = Score(out=Seq())

    score1 = Score(out=Seq())

    trac = 0
    trac1 = 0
    if direction == "north":
        hemi_power = northern_hemi_power
        latitudes = nlats
    elif direction == "south":
        hemi_power = southern_hemi_power
        latitudes = slats
    aurora_intensity_cache = [[0 for j in range(0, 360)] for i in range(0, (max(latitudes) - min(latitudes)))]
    for i in range(0, abs(min(latitudes)- max(latitudes))):
        for j in range(359, -1, -1):
            intensity = get_aurora_intensity_for_location(aurora_data, i, j)
        
            if intensity != 0:

                if direction == "north":    
                    aurora_intensity_cache[i][j] = intensity
                elif direction == "south":      
                    aurora_intensity_cache[ abs(i) -2][j] = intensity
    aic = aurora_intensity_cache   
    the_path, mxv = find_path_of_most_variance(aic)
    for h in range(len(timestamps)):
        latnotes = []
        brightness = []
        color_average = []
        for i in the_path:
          
            aint = aic[i[0]][i[1]]
            wavelength = int(getwavelength(i[0], i[1]))
            color_at_loc =  wv_to_col(wavelength)
            color_average.append(iinst[color_at_loc])
            rayleighs = (gw_to_rayleighs(wavelength, hemi_power, efficiency=0.01))
            rayleigh = rayleighs[h]
            minr = min(rayleighs)
            maxr = max(rayleighs)
            amp = rescale(rayleigh, minr, maxr, 0.2, .9)
            brightness.append(amp)
            intensity = aic[i[0]][i[1]]
            note = musx.tools.fit(intensity, 40, 110)
            latnotes.append(note)
         
            score1.add(Note(time=trac1, pitch=note, amplitude=amp, duration=0.15, instrument= iinst[color_at_loc]))
            score.add(Note(time=trac, pitch=note, amplitude=amp, duration=0.15, instrument= iinst[color_at_loc]))
            trac1 += .5
            trac += .25
       
    print("composing finished")
    file = MidiFile("asonifiy.mid", [track0, score.out]).write()
    file1 = MidiFile("brail.mid", [track0, score1.out]).write()
    print(f"Wrote '{file.pathname}'.")
    print(f"Wrote '{file1.pathname}'.")
    midi_file_path = 'asonifiy.mid'
    soundfont_path = '/Users/simoncooper/Desktop/ios_soundfont.sf2'
    
    try:
        # Start FluidSynth to play the MIDI file
        subprocess.run(['fluidsynth', '-i', '-g', '2', soundfont_path, midi_file_path])
        return jsonify({"status": "playing"}), 200
    except Exception as e:
        print(f"Error playing MIDI file: {e}")
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(port=8080)
