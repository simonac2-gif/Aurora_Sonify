import socket
from music21 import converter, braille
import os
import mido
from mido import MidiFile

# Braille music mapping (simplified example)
import os
from music21 import converter, braille



def makebraille():
    braille_output_path = os.path.join('static', 'aurora_braille.brl')
    
    midi_file_pat = '/Users/simoncooper/Desktop/Light Sonification/brail.mid'
    musicxml_output_path = "/Users/simoncooper/Desktop/Light Sonification/xmlconvert.musicxml"
    midi = MidiFile(midi_file_path)
    try:
        score = converter.parse(midi_file_path)
        score.write('musicxml', fp=musicxml_output_path)
        get_xml = converter.parse(musicxml_output_path)
        # Convert the MusicXML score to Braille transcription
        braille_output = braille.translate.objectToBraille(get_xml)
        # Save the Braille transcription to a .brl file
        with open(braille_output_path, 'w', encoding='utf-8') as braille_file:
            braille_file.write(braille_output)
       
    except Exception as e:
        print(f"Error during conversion: {e}")
        
 

if __name__ == "__main__":
    makebraille()
    