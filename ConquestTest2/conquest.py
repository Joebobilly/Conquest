import pygame
import os
import math
import time
import socket
import threading

global sock

# Storing board
with open(os.path.join('Save', 'Map', 'Land.txt'), 'r') as file:
    land_data = file.readlines()
with open(os.path.join('Save', 'Map', 'Buildings2.txt'), 'r') as file:
    building_data = file.readlines()

# Initialize the game
pygame.init()
width = 640
height = 480
xoffset = width // 32
yoffset = height // 32
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
clock = pygame.time.Clock()
pygame.display.set_caption("Conquest")
pygame.display.set_icon(pygame.image.load(os.path.join('Assets', 'Interface', 'icon.png')))
running = True

# Values
playerX = 0
playerY = 0
playerID = 1
mapWidth = 100
mapHeight = 100
global location, selectedBuilding
location = 'menu'
selectedBuilding = '1'
global powerTime, materialsTime
powerTime = time.time()
materialsTime = time.time()
global resourceTypes
resourceTypes = {
        'power': 0,
        'maxPower': 1,
        'materials': 2,
        'maxMaterials': 3
    }

# Assets
def load_assets():
    global UItext
    UItext = pygame.font.Font(os.path.join('Assets', 'Fonts', 'font.ttf'), 16)
    global crosshairSurface, grass, water
    crosshairSurface = pygame.image.load(os.path.join('Assets', 'Interface', 'crosshair.png'))
    grass = pygame.image.load(os.path.join('Assets', 'Tiles', 'Base', 'grass.png'))
    water = pygame.image.load(os.path.join('Assets', 'Tiles', 'Base', 'water.png'))

    # Player tiles
    global clay, warped_hyphae
    global blockDict
    clay = pygame.image.load(os.path.join('Assets', 'Tiles', 'Players', '1.png'))
    warped_hyphae = pygame.image.load(os.path.join('Assets', 'Tiles', 'Players', '2.png'))
    blockDict = {
        1: clay,
        2: warped_hyphae
    }

    # Buildings
    global camp, mine, materialStorage
    global buildingDict, literalBuildingDict
    camp = pygame.image.load(os.path.join('Assets', 'Buildings', 'camp.png'))
    mine = pygame.image.load(os.path.join('Assets', 'Buildings', 'mine.png'))
    materialStorage = pygame.image.load(os.path.join('Assets', 'Buildings', 'material_storage.png'))
    buildingDict = {
        '1': camp,
        '2': mine,
        '3': materialStorage

    }
    literalBuildingDict = {
        '1': 'Training Camp',
        '2': 'Mine',
        '3': 'Material Storage'
    }

    #Walls
    global wall1, wall2, wall3, wall4
    global wallDict
    wall1 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall1.png'))
    wall2 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall2.png'))
    wall3 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall3.png'))
    wall4 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall4.png'))
    wall5 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall5.png'))
    wall6 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall6.png'))
    wall7 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall7.png'))
    wall8 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall8.png'))
    wall9 = pygame.image.load(os.path.join('Assets', 'Walls', 'wall9.png'))
    wallDict = {
        1: wall1,
        2: wall2,
        3: wall3,
        4: wall4,
        5: wall5,
        6: wall6,
        7: wall7,
        8: wall8,
        9: wall9
    }
load_assets()

# Functions

#Map
def render_land(PlrX: int, PlrY: int):
    #with open(os.path.join('Save', 'Map', 'Land.txt'), 'r') as file:
    #    land_data = file.readlines()
    for y, line in enumerate(land_data, yoffset - PlrY):
        for x, char in enumerate(line.strip(), xoffset - PlrX):
            if x > screen.get_width() // 16:
                break
            if char == '0':
                screen.blit(grass, (x * 16, y * 16))
            elif char == '-':
                screen.blit(water, (x * 16, y * 16))
            else:
                screen.blit(blockDict.get(int(char)), (x * 16, y * 16))
        if y > screen.get_height() // 16:
            break

def render_buildings(PlrX: int, PlrY: int):
    #with open(os.path.join('Save', 'Map', 'Buildings2.txt'), 'r') as file:
    #    building_data = file.readlines()
    for y, line in enumerate(building_data, yoffset - PlrY):
        for x, char in enumerate(line.strip(), xoffset - PlrX):
            if x > screen.get_width() // 16:
                break
            if ord(char)>32:
                screen.blit(wallDict.get(ord(char)-32), (x * 16, y * 16))
            elif not ord(char)==0:
                screen.blit(buildingDict.get(str(ord(char))), (x * 16, y * 16))
        if y > screen.get_height() // 16:
            break

def move_player(direction: str):
    if location == 'game':
        global playerX, playerY
        if direction == 'up':
            if playerY > 0:
                playerY -= 1
        elif direction == 'down':
            if playerY < mapHeight - 1:
                playerY += 1
        elif direction == 'left':
            if playerX > 0:
                playerX -= 1
        elif direction == 'right':
            if playerX < mapWidth - 1:
                playerX += 1

def get_tile(x: int, y: int):
    #with open(os.path.join('Save', 'Map', 'land.txt'), 'r') as file:
    #    land_data = file.readlines()
    if 0 <= y < mapHeight:
        line = land_data[y].strip()
        if 0 <= x < mapWidth:
            return line[x]
    return None

def get_building(x: int, y: int):
    #with open(os.path.join('Save', 'Map', 'Buildings2.txt'), 'r') as file:
    #   building_data = file.readlines()
    if 0 <= y < mapHeight:
        line = building_data[y].strip()
        if 0 <= x < mapWidth:
            return line[x]
    return None

def set_tile(x: int, y: int, tile: str):
    #with open(os.path.join('Save', 'Map', 'land.txt'), 'r') as file:
    #   lines = file.readlines()
    targetLine = list(land_data[y])
    targetLine[x] = tile
    land_data[y] = ''.join(targetLine)
    #with open(os.path.join('Save', 'Map', 'land.txt'), 'w') as file:
    #    file.writelines(lines)

def set_building(x: int, y: int, building: str, sock=None):
    #with open(os.path.join('Save', 'Map', 'Buildings2.txt'), 'r') as file:
    #    lines = file.readlines()
    targetLine = list(building_data[y])
    targetLine[x] = building
    building_data[y] = ''.join(targetLine)
    if sock:
        sock.sendall(("Hey building update: "+str(x)+', '+str(y)).encode())
    #with open(os.path.join('Save', 'Map', 'Buildings2.txt'), 'w') as file:
    #    file.writelines(lines)

def get_cardinal(x: int, y: int):
    return [
    get_tile(x, y - 1),  # North
    get_tile(x + 1, y),  # East
    get_tile(x, y + 1),  # South
    get_tile(x - 1, y)]  # West

def get_adjacent(x: int, y: int):
    return [
        get_tile(x - 1, y - 1),  # North-West
        get_tile(x + 1, y - 1),  # North-East
        get_tile(x + 1, y + 1),  # South-East
        get_tile(x - 1, y + 1),  # South-West
        get_tile(x, y - 1),      # North
        get_tile(x + 1, y),      # East
        get_tile(x, y + 1),      # South
        get_tile(x - 1, y)]       # West

#Resources
def change_resource(type: str, amount: int):
    with open(os.path.join('Save', 'Data', 'Stats.txt')) as file:
        lines = file.readlines()
    resource = int(lines[resourceTypes.get(type)].strip())
    resource += amount
    lines[resourceTypes.get(type)] = str(resource) + '\n'
    with open(os.path.join('Save', 'Data', 'Stats.txt'), 'w') as file:
        file.writelines(lines)

def set_resource(type: str, amount: int):
    with open(os.path.join('Save', 'Data', 'Stats.txt')) as file:
        lines = file.readlines()
    lines[resourceTypes.get(type)] = str(amount) + '\n'
    with open(os.path.join('Save', 'Data', 'Stats.txt'), 'w') as file:
        file.writelines(lines)

def get_resource(type: str):
    return int(open(os.path.join('Save', 'Data', 'Stats.txt')).readlines()[resourceTypes.get(type)].strip())

def count_building(type: str, ID: int):
    #with open(os.path.join('Save', 'Map', 'Buildings2.txt'), 'r') as file:
    #    building_data = file.readlines()
    count = 0
    iter1 = 0
    for list_row in building_data:
        list_char = list(list_row)
        if '\n' in list_char:
            list_char.remove('\n')
        iter2 = 0
        for tile in list_char:
            if tile == type:
                if get_tile(iter2, iter1) == str(ID):
                    count += 1
            iter2 += 1
        iter1 += 1
    return count

#Attacking
def near_water(x, y, ID):
    if str(ID) in get_adjacent(x, y) and not str(ID) == get_tile(x, y):
        return False
    elif '-' in get_cardinal(x, y):
        return True
    else:
        return False

def tool_attack(x: int, y: int, ID: int):
    if str(ID) in get_adjacent(x, y):
        if get_tile(x, y) == '0':
            expand(x, y, ID, False)
        elif get_tile(x, y) == '-':
            pass
        else:
            attack(x, y, ID, False)
    elif near_water(x, y, ID):
        if get_tile(x, y) == '0':
            expand(x, y, ID, True)
        elif get_tile(x, y) == '-':
            pass
        else:
            attack(x, y, ID, True)

def expand(x: int, y: int, ID: int, water: bool):
    if water:
        if get_resource('power') >= 20:
            set_tile(x, y, str(ID))
            change_resource('power', -20)
    else:
        if get_resource('power') >= 5:
            set_tile(x, y, str(ID))
            change_resource('power', -5)

def attack(x: int, y: int, ID: int, water: bool):
    power = get_resource('power')
    attackCost = attack_cost(x, y, ID, water)
    if str(attackCost).isdigit():
        if power >= attackCost and not get_tile(x, y) == str(ID):
            building = get_building(x, y)
            if ord(building)>32:
                if ord(building)-32 > 1:
                    set_building(x, y, str(ord(building) - 33))
                else:
                    set_building(x, y, 0)
            else:
                set_tile(x, y, str(ID))
            change_resource('power', -attackCost)

def attack_cost(x: int, y: int, ID: int, water: bool):
    tile = get_tile(x, y)
    if tile == '-':
        return None
    elif tile == '0':
        if water:
            cost = 20
            return cost
        else:
            cost = 5
            return cost
    else:
        building = get_building(x, y)
        if building.isdigit():
            cost = 15
            wallFee = int(building) ** 2
            cost += wallFee
            if water:
                cost += 15
            return cost
        else:
            cost = 15
            if water:
                cost += 15
            return cost

#Construction
def tool_build(x: int, y: int, building: str, ID: int):
    cost = construct_cost(building, ID)
    materials = get_resource('materials')
    if get_building(x, y) == chr(0) and get_tile(x, y) == str(ID):
        print('passed')
        if materials >= cost:
            if sock:
                set_building(x, y, chr(int(building)),sock=sock)
            else:
                set_building(x, y, chr(int(building)))
            change_resource('materials', -cost)

def construct_cost(building: str, ID: int):
    count = count_building(chr(int(building)), ID)
    cost = 0
    if building == '1': #Camp
        cost = 25
        cost += count * 25
        return cost
    elif building == '2': #Mine
        cost = 20
        cost += count * 20
        return cost
    elif building == '3': #Material Storage
        cost = 100
        cost += count * 20
        return cost
    else:
        return None

def build_wall(x, y, ID):
    tile = get_tile(x, y)
    building = get_building(x, y)
    print(ord(building))
    print('')
    materials = get_resource('materials')
    if tile == str(ID):
        if ord(building) == 0:
            cost = wall_cost(x, y)
            if materials >= cost:
                set_building(x, y, chr(33))
                change_resource('materials', -cost)
        elif ord(building)>32:
            cost = wall_cost(x, y)
            if materials >= cost:
                set_building(x, y, chr(ord(building)+1))
                change_resource('materials', -cost)
                


def wall_cost(x, y):
    building = ord(get_building(x, y))
    if building == 0:
        return 10
    elif not building>32:
        return None
    else:
        cost = 10
        cost += 2 ** int(building-32)
        return cost

def lfi(sock):
    ulo=time.time()
    while time.time()-ulo<0.1:
        pass
    sock.sendall('RECV'.encode())
def listen_for_messages(sock):
    done=0
    while True:
        try:
            
            message = sock.recv(1048576).decode()
            
            if message and '..' in message:
                message=message[2:]
                for i in range(int(len(message)/3)):
                    x=0
                    while x<len(message):
                        if ord(message[x])>99:
                            x1=ord(message[x])-100
                            y=ord(message[x+1])
                            rt=''
                            for i in message[x+2:].split(chr(0))[0]:
                                set_building(x1,y,i)
                                x1+=1
                            x+=len(message[x+2:].split(chr(0))[0])+3
                        else:
                            set_building(ord(message[x]),ord(message[x+1]),message[x+2])
                            x+=3
            elif message:
                eval(message)
        except Exception as e:
            print(e)
            print("[ERROR] Lost connection to server.")
            sock.close()
            break
def initclient(server_ip='127.0.0.1', server_port=12345):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, server_port))
        sock.sendall("JOIN".encode())
        threading.Thread(target=listen_for_messages, args=(sock,), daemon=True).start()
        threading.Thread(target=lfi, args=(sock,), daemon=True).start()
        return sock
    except Exception as e:
        print(e)
        print("No server started, starting offline")
        return None
sock=initclient()
# Main game loop
while running:
    # Check for events
    for event in pygame.event.get():
        # Mostly UI events
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_RETURN:
                if location == 'menu':
                    location = 'game'
            # Movement controls
            if not (pygame.key.get_pressed()[pygame.K_LSHIFT]):
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    move_player('up')
                if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    move_player('down')
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    move_player('left')
                if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    move_player('right')
            # Game interaction
            if location == 'game':
                if event.key == pygame.K_e: #Attack
                    tool_attack(playerX, playerY, playerID)
                if event.key == pygame.K_r: #Place building
                    tool_build(playerX, playerY, selectedBuilding, playerID)
                if event.key == pygame.K_q: #Build wall
                    build_wall(playerX, playerY, playerID)
                if event.key == pygame.K_1:
                    selectedBuilding = '1'
                if event.key == pygame.K_2:
                    selectedBuilding = '2'
                if event.key == pygame.K_3:
                    selectedBuilding = '3'


    # Sprinting controls
    if pygame.key.get_pressed()[pygame.K_LSHIFT]:
        if pygame.key.get_pressed()[pygame.K_UP] or pygame.key.get_pressed()[pygame.K_w]:
            move_player('up')
        if pygame.key.get_pressed()[pygame.K_DOWN] or pygame.key.get_pressed()[pygame.K_s]:
            move_player('down')
        if pygame.key.get_pressed()[pygame.K_LEFT] or pygame.key.get_pressed()[pygame.K_a]:
            move_player('left')
        if pygame.key.get_pressed()[pygame.K_RIGHT] or pygame.key.get_pressed()[pygame.K_d]:
            move_player('right')
            


    # Clear the screen
    screen.fill((64, 64, 64))
    # Draw the game elements based on the current location
    xoffset = screen.get_width() // 32
    yoffset = screen.get_height() // 32
    width = screen.get_width()
    height = screen.get_height()
    if location == 'game':
        # Draw the game background
        screen.fill((64, 64, 64))

        # Render the land
        render_land(playerX, playerY)
        render_buildings(playerX, playerY)

        # Draw the crosshair
        screen.blit(crosshairSurface, (xoffset * 16, yoffset * 16))

        # UI elements
        powerDisplay = UItext.render("Power: " + str(get_resource('power')) + '/' + str(get_resource('maxPower')), True, (255, 85, 85))
        screen.blit(powerDisplay, (0, 0))
        materialsDisplay = UItext.render("Materials: " + str(get_resource('materials')) + '/' + str(get_resource('maxMaterials')), True, (255, 170, 0))
        screen.blit(materialsDisplay, (0, 32))
        if get_tile(playerX, playerY).isdigit() and not int(get_tile(playerX, playerY)) == playerID:
            attackCost = UItext.render("Attack Cost: " + str(attack_cost(playerX, playerY, playerID, near_water(playerX, playerY, playerID))), True, (255, 85, 85))
        else:
            attackCost = UItext.render("Attack Cost: " + str(attack_cost(playerX, playerY, playerID, near_water(playerX, playerY, playerID))), True, (128, 128, 128))
        screen.blit(attackCost, (0, 16))
        buildingDisplay = UItext.render("Selected Building: " + str(literalBuildingDict.get(selectedBuilding)) + ' (' + str(construct_cost(selectedBuilding, playerID)) + ')', True, (255, 170, 0))
        screen.blit(buildingDisplay, (0, 48))
        if not get_building(playerX, playerY) == '-' and not get_building(playerX, playerY).isdigit() or not get_tile(playerX, playerY) == str(playerID):
            wallCost = UItext.render("Wall Cost: N/A", True, (128, 128, 12))
        else:
            wallCost = UItext.render("Wall Cost: " + str(wall_cost(playerX, playerY)), True, (255, 170, 0))
        screen.blit(wallCost, (0, 64))

        # Resource loop

        # Power
        if time.time() - powerTime > 4:
            maxPower = get_resource('maxPower')
            power = get_resource('power')
            if power < maxPower:
                change_resource('power', count_building(chr(1), playerID) + 1)
            if get_resource('power') > maxPower:
                set_resource('power', maxPower)
            powerTime = time.time()

        # Materials
        if time.time() - materialsTime > 1:
            additionalMax = count_building(chr(3), playerID) * 20
            print(additionalMax)
            set_resource('maxMaterials', 100 + additionalMax)
            maxMaterials = get_resource('maxMaterials')
            materials = get_resource('materials')
            if materials < maxMaterials:
                change_resource('materials', count_building(chr(2), playerID) + 1)
            if get_resource('materials') > maxMaterials:
                set_resource('materials', maxMaterials)
            materialsTime = time.time()


    if location == 'menu':

        # Draw the title
        bigFont = pygame.font.Font(os.path.join('Assets', 'Fonts', 'font.ttf'), 48)
        title_text = bigFont.render("Conquest", True, (88, 255, 88))
        screen.blit(title_text, (width // 2 - title_text.get_width() // 2, height // 4))

        # Draw the play button
        medFont = pygame.font.Font(os.path.join('Assets', 'Fonts', 'font.ttf'), 32)
        play_text = medFont.render("Press Enter to Play", True, (255, 255, 255))
        screen.blit(play_text, (width // 2 - play_text.get_width() // 2, height // 2))


    #print(clock.get_fps())
    pygame.display.flip()
    clock.tick(60)
#Saving board
with open(os.path.join('Save', 'Map', 'Land.txt'), 'w') as file:
    file.write(''.join(land_data))
with open(os.path.join('Save', 'Map', 'Buildings2.txt'), 'w') as file:
    file.write(''.join(building_data))
pygame.quit()
if sock:
    sock.sendall("EXIT".encode())
    sock.close()
