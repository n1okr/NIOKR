#!/usr/bin/env python3
"""
GENCAD Parser

This script parses GENCAD files (.cad) and extracts pin placements, names, and connections.
It outputs CSV files that can be imported into Houdini or other tools for PCB routing visualization.

Usage:
    python gencad_parser.py [input_file]

Output:
    - pins.csv: Contains all pin data (component, pin name, x, y, layer, signal)
    - connections.csv: Contains all connections between pins
    - netlist.csv: Contains netlist information for each signal

Author: Claude AI Assistant
Date: 2023
"""

import re
import csv
import os
import math
import logging
import argparse
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gencad_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GencadParser")

class GencadParser:
    """
    Parser for GENCAD files (.cad) that extracts pin placements, names, and connections.
    
    Attributes:
        file_path (str): Path to the GENCAD file
        pins (list): List of pin data dictionaries
        signals (dict): Dictionary of signal connections
        components (dict): Dictionary of component data
        shapes (dict): Dictionary of shape data with pin definitions
        units (str): Units used in the GENCAD file (default: INCH)
    """
    
    def __init__(self, file_path):
        """
        Initialize the GENCAD parser.
        
        Args:
            file_path (str): Path to the GENCAD file
        """
        self.file_path = file_path
        self.pins = []  # Will store pin data: [component, pin_name, x, y, layer]
        self.signals = defaultdict(list)  # Will store signal connections
        self.components = {}  # Will store component data: {name: {position, rotation, etc.}}
        self.shapes = {}  # Will store shape data with pin definitions
        self.units = "INCH"  # Default units
        self.board_outline = []  # Will store board outline points
        
    def parse(self):
        """
        Parse the GENCAD file and extract pin information.
        
        This method reads the GENCAD file and extracts information from the following sections:
        - HEADER: Units and other general information
        - BOARD: Board outline
        - SHAPES: Component shapes and pin definitions
        - COMPONENTS: Component placements
        - SIGNALS: Signal connections
        
        After parsing, it calculates the actual pin positions based on component placement and shape definitions.
        
        Raises:
            FileNotFoundError: If the GENCAD file is not found
            Exception: If there is an error parsing the file
        """
        try:
            with open(self.file_path, 'r') as file:
                content = file.read()
                
            # Parse header section to get units
            header_section = self._extract_section(content, "HEADER", "ENDHEADER")
            self._parse_header(header_section)
            logger.info(f"Using units: {self.units}")
            
            # Parse board section to get outline
            board_section = self._extract_section(content, "BOARD", "ENDBOARD")
            self._parse_board(board_section)
            logger.info(f"Parsed board outline with {len(self.board_outline)} points")
            
            # Parse shapes section to get pin definitions
            shapes_section = self._extract_section(content, "SHAPES", "ENDSHAPES")
            self._parse_shapes(shapes_section)
            logger.info(f"Parsed {len(self.shapes)} shapes")
            
            # Parse components section to get component placements
            components_section = self._extract_section(content, "COMPONENTS", "ENDCOMPONENTS")
            self._parse_components(components_section)
            logger.info(f"Parsed {len(self.components)} components")
            
            # Parse signals section to get connections
            signals_section = self._extract_section(content, "SIGNALS", "ENDSIGNALS")
            self._parse_signals(signals_section)
            logger.info(f"Parsed {len(self.signals)} signals")
            
            # Calculate actual pin positions based on component placement and shape definitions
            self._calculate_pin_positions()
            logger.info(f"Calculated positions for {len(self.pins)} pins")
            
        except FileNotFoundError:
            logger.error(f"GENCAD file not found: {self.file_path}")
            raise
        except Exception as e:
            logger.error(f"Error parsing file: {str(e)}", exc_info=True)
            raise
    
    def _extract_section(self, content, start_marker, end_marker):
        """
        Extract a section from the GENCAD file.
        
        Args:
            content (str): Content of the GENCAD file
            start_marker (str): Start marker of the section
            end_marker (str): End marker of the section
            
        Returns:
            str: Content of the section
        """
        pattern = f"\\${start_marker}(.*?)\\${end_marker}"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        logger.warning(f"Section {start_marker} not found in file")
        return ""
    
    def _parse_header(self, header_section):
        """
        Parse the HEADER section to extract units.
        
        Args:
            header_section (str): Content of the HEADER section
        """
        lines = header_section.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("UNITS"):
                parts = line.split()
                if len(parts) > 1:
                    self.units = parts[1]
                    break
    
    def _parse_board(self, board_section):
        """
        Parse the BOARD section to extract board outline.
        
        Args:
            board_section (str): Content of the BOARD section
        """
        lines = board_section.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for LINE definition (board outline)
            line_match = re.match(r'LINE\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)', line)
            if line_match:
                x1, y1, x2, y2 = map(float, line_match.groups())
                self.board_outline.append((x1, y1, x2, y2))
    
    def _parse_shapes(self, shapes_section):
        """
        Parse the SHAPES section to extract pin definitions.
        
        Args:
            shapes_section (str): Content of the SHAPES section
        """
        # Split into individual shapes
        current_shape = None
        lines = shapes_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for shape definition
            shape_match = re.match(r'SHAPE\s+"([^"]+)"', line)
            if shape_match:
                current_shape = shape_match.group(1)
                self.shapes[current_shape] = {'pins': []}
                continue
                
            # Check for pin definition
            pin_match = re.match(r'PIN\s+"([^"]+)"\s+(\w+)\s+([-\d\.]+)\s+([-\d\.]+)(?:\s+(\w+))?(?:\s+(\d+))?(?:\s+(\d+))?', line)
            if pin_match and current_shape:
                groups = pin_match.groups()
                pin_name, pad_type, x, y = groups[0:4]
                layer = groups[4] if len(groups) > 4 and groups[4] else "TOP"
                rotation = int(groups[5]) if len(groups) > 5 and groups[5] else 0
                
                self.shapes[current_shape]['pins'].append({
                    'name': pin_name,
                    'pad': pad_type,
                    'x': float(x),
                    'y': float(y),
                    'layer': layer,
                    'rotation': rotation
                })
    
    def _parse_components(self, components_section):
        """
        Parse the COMPONENTS section to extract component placements.
        
        Args:
            components_section (str): Content of the COMPONENTS section
        """
        current_component = None
        lines = components_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for component definition
            comp_match = re.match(r'COMPONENT\s+"([^"]+)"', line)
            if comp_match:
                current_component = comp_match.group(1)
                self.components[current_component] = {
                    'mirror_x': False,
                    'mirror_y': False,
                    'flip': False
                }
                continue
                
            # Check for device definition
            device_match = re.match(r'DEVICE\s+"([^"]+)"', line)
            if device_match and current_component:
                device = device_match.group(1)
                self.components[current_component]['device'] = device
                continue
                
            # Check for placement
            place_match = re.match(r'PLACE\s+([-\d\.]+)\s+([-\d\.]+)', line)
            if place_match and current_component:
                x, y = place_match.groups()
                self.components[current_component]['x'] = float(x)
                self.components[current_component]['y'] = float(y)
                continue
                
            # Check for layer
            layer_match = re.match(r'LAYER\s+(\w+)', line)
            if layer_match and current_component:
                layer = layer_match.group(1)
                self.components[current_component]['layer'] = layer
                continue
                
            # Check for rotation
            # Handle both integer and float rotations
            rot_match = re.match(r'ROTATION\s+([-\d\.]+)', line)
            if rot_match and current_component:
                rotation = rot_match.group(1)
                try:
                    self.components[current_component]['rotation'] = int(float(rotation))
                except ValueError:
                    logger.warning(f"Invalid rotation value for component {current_component}: {rotation}")
                    self.components[current_component]['rotation'] = 0
                continue
                
            # Check for shape
            shape_match = re.match(r'SHAPE\s+"([^"]+)"', line)
            if shape_match and current_component:
                shape = shape_match.group(1)
                self.components[current_component]['shape'] = shape
                continue
                
            # Check for mirroring and flipping
            if "MIRRORX" in line and current_component:
                self.components[current_component]['mirror_x'] = True
            if "MIRRORY" in line and current_component:
                self.components[current_component]['mirror_y'] = True
            if "FLIP" in line and current_component:
                self.components[current_component]['flip'] = True
    
    def _parse_signals(self, signals_section):
        """
        Parse the SIGNALS section to extract connections.
        
        Args:
            signals_section (str): Content of the SIGNALS section
        """
        current_signal = None
        lines = signals_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for signal definition
            signal_match = re.match(r'SIGNAL\s+"([^"]+)"', line)
            if signal_match:
                current_signal = signal_match.group(1)
                continue
                
            # Check for node connection
            node_match = re.match(r'NODE\s+"([^"]+)"\s+"([^"]+)"', line)
            if node_match and current_signal:
                component, pin = node_match.groups()
                self.signals[current_signal].append((component, pin))
    
    def _calculate_pin_positions(self):
        """
        Calculate actual pin positions based on component placement and rotation.
        
        This method applies the following transformations to pin coordinates:
        1. Mirroring (if applicable)
        2. Rotation
        3. Translation
        
        It also determines the pin layer based on the component layer and flip status.
        """
        for comp_name, comp_data in self.components.items():
            if 'shape' not in comp_data:
                logger.warning(f"Component {comp_name} has no shape defined")
                continue
                
            shape_name = comp_data['shape']
            if shape_name not in self.shapes:
                logger.warning(f"Shape {shape_name} not found for component {comp_name}")
                continue
                
            comp_x = comp_data['x']
            comp_y = comp_data['y']
            rotation = comp_data.get('rotation', 0)
            mirror_x = comp_data.get('mirror_x', False)
            mirror_y = comp_data.get('mirror_y', False)
            flip = comp_data.get('flip', False)
            comp_layer = comp_data.get('layer', 'TOP')
            
            # Check if this is a diode component
            is_diode = comp_name.startswith("L-D")
            
            # If it's a diode, we need to collect all pins first to swap them later
            diode_pins = []
            
            for pin in self.shapes[shape_name]['pins']:
                # Apply mirroring if needed
                pin_x = pin['x']
                pin_y = pin['y']
                
                if mirror_x:
                    pin_x = -pin_x
                if mirror_y:
                    pin_y = -pin_y
                
                # Apply rotation
                pin_x, pin_y = self._rotate_point(pin_x, pin_y, rotation)
                
                # Apply translation
                abs_x = comp_x + pin_x
                abs_y = comp_y + pin_y
                
                # Determine pin layer
                pin_layer = pin.get('layer', 'TOP')
                if flip:
                    pin_layer = 'BOTTOM' if pin_layer == 'TOP' else 'TOP'
                
                # Store pin data
                pin_data = {
                    'component': comp_name,
                    'pin_name': pin['name'],
                    'x': abs_x,
                    'y': abs_y,
                    'layer': pin_layer,
                    'signal': self._find_signal(comp_name, pin['name'])
                }
                
                if is_diode:
                    diode_pins.append(pin_data)
                else:
                    self.pins.append(pin_data)
            
            # If this is a diode and we have exactly 2 pins, swap their coordinates
            if is_diode and len(diode_pins) == 2:
                # Make sure pins are sorted by pin_name
                diode_pins.sort(key=lambda p: p['pin_name'])
                
                # Swap x and y coordinates between pin 1 and pin 2
                x1, y1 = diode_pins[0]['x'], diode_pins[0]['y']
                x2, y2 = diode_pins[1]['x'], diode_pins[1]['y']
                
                diode_pins[0]['x'], diode_pins[0]['y'] = x2, y2
                diode_pins[1]['x'], diode_pins[1]['y'] = x1, y1
                
                # Log the swap for debugging
                logger.info(f"Swapped coordinates for diode {comp_name}: Pin 1 now at ({diode_pins[0]['x']}, {diode_pins[0]['y']}), Pin 2 now at ({diode_pins[1]['x']}, {diode_pins[1]['y']})")
                
                # Add the pins to the main list
                self.pins.extend(diode_pins)
            elif is_diode:
                # If it's a diode but doesn't have exactly 2 pins, add them without swapping
                self.pins.extend(diode_pins)
    
    def _rotate_point(self, x, y, angle_deg):
        """
        Rotate a point around the origin.
        
        Args:
            x (float): X coordinate
            y (float): Y coordinate
            angle_deg (float): Rotation angle in degrees
            
        Returns:
            tuple: Rotated coordinates (x, y)
        """
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        new_x = x * cos_a - y * sin_a
        new_y = x * sin_a + y * cos_a
        
        return new_x, new_y
    
    def _find_signal(self, component, pin):
        """
        Find the signal name for a given component and pin.
        
        Args:
            component (str): Component name
            pin (str): Pin name
            
        Returns:
            str: Signal name or "unconnected" if not found
        """
        for signal_name, connections in self.signals.items():
            if (component, pin) in connections:
                return signal_name
        return "unconnected"
    
    def export_to_csv(self, output_path):
        """
        Export pin data to CSV file.
        
        Args:
            output_path (str): Path to the output CSV file
            
        Raises:
            Exception: If there is an error exporting to CSV
        """
        try:
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = ['component', 'pin_name', 'x', 'y', 'layer', 'signal']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for pin in self.pins:
                    writer.writerow(pin)
            
            logger.info(f"Exported {len(self.pins)} pins to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting pins to CSV: {str(e)}", exc_info=True)
            raise
        
    def export_connections_to_csv(self, output_path):
        """
        Export connection data to CSV file.
        
        Args:
            output_path (str): Path to the output CSV file
            
        Raises:
            Exception: If there is an error exporting to CSV
        """
        try:
            connections = []
            
            # Group pins by signal
            signal_pins = defaultdict(list)
            for pin in self.pins:
                signal = pin['signal']
                if signal != "unconnected":
                    signal_pins[signal].append(pin)
            
            # Create connections between pins with the same signal
            for signal, pins in signal_pins.items():
                for i in range(len(pins)):
                    for j in range(i+1, len(pins)):
                        pin1 = pins[i]
                        pin2 = pins[j]
                        connections.append({
                            'signal': signal,
                            'component1': pin1['component'],
                            'pin1': pin1['pin_name'],
                            'x1': pin1['x'],
                            'y1': pin1['y'],
                            'layer1': pin1['layer'],
                            'component2': pin2['component'],
                            'pin2': pin2['pin_name'],
                            'x2': pin2['x'],
                            'y2': pin2['y'],
                            'layer2': pin2['layer']
                        })
            
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = ['signal', 'component1', 'pin1', 'x1', 'y1', 'layer1', 'component2', 'pin2', 'x2', 'y2', 'layer2']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for connection in connections:
                    writer.writerow(connection)
            
            logger.info(f"Exported {len(connections)} connections to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting connections to CSV: {str(e)}", exc_info=True)
            raise

    def export_netlist_to_csv(self, output_path):
        """
        Export netlist data to CSV file.
        
        Args:
            output_path (str): Path to the output CSV file
            
        Raises:
            Exception: If there is an error exporting to CSV
        """
        try:
            netlist = []
            
            # Create a list of all pins in each signal
            for signal_name, connections in self.signals.items():
                signal_pins = []
                for component, pin in connections:
                    # Find the pin data
                    pin_data = None
                    for p in self.pins:
                        if p['component'] == component and p['pin_name'] == pin:
                            pin_data = p
                            break
                    
                    if pin_data:
                        signal_pins.append({
                            'component': component,
                            'pin': pin,
                            'x': pin_data['x'],
                            'y': pin_data['y'],
                            'layer': pin_data['layer']
                        })
                
                netlist.append({
                    'signal': signal_name,
                    'pin_count': len(signal_pins),
                    'pins': signal_pins
                })
            
            # Export to CSV
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = ['signal', 'pin_count', 'components']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for net in netlist:
                    # Format the components as a string
                    components = ', '.join([f"{p['component']}:{p['pin']}" for p in net['pins']])
                    writer.writerow({
                        'signal': net['signal'],
                        'pin_count': net['pin_count'],
                        'components': components
                    })
            
            logger.info(f"Exported {len(netlist)} nets to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting netlist to CSV: {str(e)}", exc_info=True)
            raise

    def export_board_outline_to_csv(self, output_path):
        """
        Export board outline to CSV file.
        
        Args:
            output_path (str): Path to the output CSV file
            
        Raises:
            Exception: If there is an error exporting to CSV
        """
        try:
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = ['x1', 'y1', 'x2', 'y2']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for x1, y1, x2, y2 in self.board_outline:
                    writer.writerow({
                        'x1': x1,
                        'y1': y1,
                        'x2': x2,
                        'y2': y2
                    })
            
            logger.info(f"Exported board outline with {len(self.board_outline)} segments to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting board outline to CSV: {str(e)}", exc_info=True)
            raise

    def export_houdini_csv(self, output_path):
        """
        Export pin data to a single CSV file optimized for Houdini's tableimport.
        
        Creates a CSV where each row is a pin with position, metadata, and connection attributes.
        
        Args:
            output_path (str): Path to the output CSV file
            
        Raises:
            Exception: If there is an error exporting to CSV
        """
        try:
            # Add a unique ID to each pin
            for i, pin in enumerate(self.pins):
                pin['id'] = i
                
                # Add z coordinate based on layer (for 3D visualization)
                pin['z'] = 0.0 if pin['layer'] == 'TOP' else -0.1
                
                # Initialize connection fields
                pin['connected_to'] = []
                pin['connected_ids'] = []
            
            # Create a lookup dictionary for pins by component and pin name
            pin_lookup = {}
            for pin in self.pins:
                key = (pin['component'], pin['pin_name'])
                pin_lookup[key] = pin
            
            # Create a lookup dictionary for pins by ID
            id_lookup = {pin['id']: pin for pin in self.pins}
            
            # Create a dictionary to store connections by signal
            signal_connections = {}
            
            # Process all connections
            for signal_name, connections_list in self.signals.items():
                if signal_name == "unconnected":
                    continue
                
                # Get all pins for this signal
                signal_pins = []
                for component, pin_name in connections_list:
                    key = (component, pin_name)
                    if key in pin_lookup:
                        signal_pins.append(pin_lookup[key])
                
                # Store the pins for this signal
                signal_connections[signal_name] = signal_pins
                
                # Add connection information to each pin
                for i, pin1 in enumerate(signal_pins):
                    connected_to = []
                    connected_ids = []
                    
                    for j, pin2 in enumerate(signal_pins):
                        if i != j:  # Don't connect to self
                            connected_to.append(f"{pin2['component']}:{pin2['pin_name']}")
                            connected_ids.append(pin2['id'])
                    
                    pin1['connected_to'] = "|".join(connected_to)
                    # Format connected_ids as a proper array string [1,2,3]
                    pin1['connected_ids'] = f"[{','.join(map(str, connected_ids))}]"
            
            # Log some statistics
            connected_pins = sum(1 for pin in self.pins if pin['signal'] != "unconnected")
            logger.info(f"Found {connected_pins} connected pins out of {len(self.pins)} total pins")
            logger.info(f"Found {len(signal_connections)} signals with connections")
            
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = ['id', 'x', 'y', 'z', 'component', 'pin_name', 'layer', 'signal', 'connected_to', 'connected_ids']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for pin in self.pins:
                    # Make sure connected_ids is properly formatted as an array
                    if isinstance(pin['connected_ids'], list):
                        pin['connected_ids'] = f"[{','.join(map(str, pin['connected_ids']))}]"
                    writer.writerow(pin)
            
            logger.info(f"Exported {len(self.pins)} pins to single Houdini-friendly CSV: {output_path}")
        except Exception as e:
            logger.error(f"Error exporting to Houdini CSV: {str(e)}", exc_info=True)
            raise


def main():
    """
    Main function to parse GENCAD file and export data to CSV files.
    """
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Parse GENCAD file and export pin placements, names, and connections to CSV files.')
        parser.add_argument('input_file', nargs='?', help='Path to the GENCAD file')
        args = parser.parse_args()
        
        # Get the input file path
        if args.input_file:
            input_file = args.input_file
        else:
            # Get the directory of the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if not script_dir:
                script_dir = os.getcwd()
            input_file = os.path.join(script_dir, "NIOKR.cad")
        
        # Output file paths
        output_dir = os.path.dirname(os.path.abspath(input_file))
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_pins = os.path.join(output_dir, f"{base_name}_pins.csv")
        output_connections = os.path.join(output_dir, f"{base_name}_connections.csv")
        output_netlist = os.path.join(output_dir, f"{base_name}_netlist.csv")
        output_board_outline = os.path.join(output_dir, f"{base_name}_board_outline.csv")
        output_houdini = os.path.join(output_dir, f"{base_name}_houdini.csv")
        
        logger.info(f"Starting GENCAD parser for file: {input_file}")
        
        # Check if input file exists
        if not os.path.isfile(input_file):
            logger.error(f"Input file not found: {input_file}")
            print(f"Error: Input file not found: {input_file}")
            return
        
        # Parse the GENCAD file
        parser = GencadParser(input_file)
        parser.parse()
        
        # Export data to CSV files
        parser.export_to_csv(output_pins)
        parser.export_connections_to_csv(output_connections)
        parser.export_netlist_to_csv(output_netlist)
        parser.export_board_outline_to_csv(output_board_outline)
        parser.export_houdini_csv(output_houdini)
        
        logger.info("GENCAD parsing completed successfully")
        print("GENCAD parsing completed successfully")
        print(f"Output files: \n- {output_pins}\n- {output_connections}\n- {output_netlist}\n- {output_board_outline}\n- {output_houdini}")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main() 