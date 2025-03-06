#!/usr/bin/env python3
"""
Swap Diode Pin Coordinates

This script reads the NIOKR_houdini.csv file and swaps the coordinates for diode pins.
It creates a new file with the swapped coordinates.

Usage:
    python swap_diode_pins.py
"""

import csv
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def swap_diode_pins(input_file, output_file):
    """
    Swap the coordinates for diode pins in the CSV file.
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str): Path to the output CSV file
    """
    # Read the CSV file
    with open(input_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
    
    # Group pins by component
    components = {}
    for row in rows:
        component = row['component']
        if component not in components:
            components[component] = []
        components[component].append(row)
    
    # Swap coordinates for diode pins
    swap_count = 0
    for component, pins in components.items():
        # Check if this is a diode component
        if component.startswith('L-D') and len(pins) == 2:
            # Sort pins by pin_name
            pins.sort(key=lambda p: p['pin_name'])
            
            # Swap x and y coordinates
            x1, y1 = pins[0]['x'], pins[0]['y']
            x2, y2 = pins[1]['x'], pins[1]['y']
            
            pins[0]['x'], pins[0]['y'] = x2, y2
            pins[1]['x'], pins[1]['y'] = x1, y1
            
            logger.info(f"Swapped coordinates for diode {component}: Pin {pins[0]['pin_name']} now at ({pins[0]['x']}, {pins[0]['y']}), Pin {pins[1]['pin_name']} now at ({pins[1]['x']}, {pins[1]['y']})")
            swap_count += 1
    
    # Write the updated CSV file
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"Swapped coordinates for {swap_count} diode components")
    logger.info(f"Wrote updated CSV to {output_file}")

def main():
    """
    Main function to swap diode pin coordinates.
    """
    input_file = "NIOKR_houdini.csv"
    output_file = "NIOKR_houdini_fixed.csv"
    
    if not os.path.isfile(input_file):
        logger.error(f"Input file not found: {input_file}")
        return
    
    swap_diode_pins(input_file, output_file)

if __name__ == "__main__":
    main() 