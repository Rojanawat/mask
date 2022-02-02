import sensor,image,lcd,time
import KPU as kpu
from Maix import I2S, GPIO
from fpioa_manager import fm
from machine import UART
import struct
from time import sleep_ms, ticks_ms, ticks_diff
from Dude import dude, PORT

######## UART for Temperature
fm.register (12, fm.fpioa.UART1_TX)
fm.register (13, fm.fpioa.UART1_RX)
uart_temp = UART (UART.UART1, 115200, 8, None, 1, timeout = 1000, read_buf_len = 4096)

######## GPIO For trig thermometer
fm.register(10,  fm.fpioa.GPIO1, force=True)
triger=GPIO(GPIO.GPIO1,GPIO.OUT)
triger.value(0)


######## Config Camera and Display
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_windowing((320, 224))
sensor.set_vflip(0)
sensor.run(1)
lcd.init(type=1, freq=15000000, color=lcd.BLACK)
lcd.rotation(1)

######### config facemask detection
task = kpu.load(0x400000)
a = kpu.set_outputs(task, 0, 10,7,35)
anchor = (0.212104,0.261834, 0.630488,0.706821, 1.264643,1.396262, 2.360058,2.507915, 4.348460,4.007944)
a = kpu.init_yolo2(task, 0.5, 0.5, 5, anchor)

######### config detection
stage = 0
# 0 = init
# 1 = wait for user waring mask
# 2 = wait for approching
# 3 = wait for approching
# 4 = check temperature

# time out unmask
timestamp = 0
timeout_wait_mask = 5000 # ms
timeout_wait_approch = 5000 # ms
timeout_wait_check = 5000 # ms
sleep_between_person = 3 # sec
#face_size_threshold_w = 50
#face_size_threshold_h = 50
face_size_threshold_w = 50
face_size_threshold_h = 59

body = 0
thislist = []

while(True):
    img = sensor.snapshot()
    a = img.pix_to_ai()
    # face detection
    faces = kpu.run_yolo2(task, img)
    classid = -1
    if faces: #found face in screen
        face = faces[0] # first face only
        classid = face.classid()
        x,y,w,h = face.rect()
        if classid == 0:
            a=img.draw_rectangle(face.rect(),color = (255, 0, 0),thickness=5)
        else:
            a=img.draw_rectangle(face.rect(),color = (0, 255, 0),thickness=5)


    #--------- State -----------------------------------------------


    if classid == 0 and stage == 0: # detect face not wearing mask
        #player.play(0, 1)
        stage = 1
        timestamp = time.ticks_ms()#stamp time
    elif stage == 1: # wait for user waring mask
        if classid == 1: #user wearing mask
            stage = 2
            timestamp = time.ticks_ms()#stamp time
        elif time.ticks_ms() - timestamp > timeout_wait_mask:
            stage = 0 # reset
    elif classid == 1 and (stage == 2 or stage == 0): # ask for approching
        #player.play(0, 2)
        stage = 3
        timestamp = time.ticks_ms()#stamp time
    elif classid == 1 and stage == 3: # wait for approching
        if w > face_size_threshold_w and h > face_size_threshold_h:
            stage = 4
            timestamp = time.ticks_ms()#stamp time
        elif time.ticks_ms() - timestamp > timeout_wait_approch:
            stage = 0 # reset
    elif stage == 4: # check temperature
        a = img.draw_circle(112+49,112+8,58,(128, 128, 128), 3)
        #####################################
        triger.value(1)
        time.sleep(0.001)
        triger.value(0)
        rx = uart_temp.read(7)



        if body == 1 :
            print ("Temperature : ",rx)
            some_bad_bytes = rx
            temp_text = str( some_bad_bytes )[2:7]

            temp_float = float(temp_text)
            print("Temp float : ",temp_float)
            body = 0
            temperature = temp_float

            if temperature < 37.5 :
                #player.play(0, 3)
                print ("Temperature : %2.1f",temperature)
                stage = 0 # reset

                dude.Servo(PORT.OUTPUT1,1,0)
                time.sleep(2)
                dude.Servo(PORT.OUTPUT1,1,90)
                time.sleep(2)
                dude.Servo(PORT.OUTPUT1,1,0)
                time.sleep(2)
            elif temperature >= 37.5 :
                #player.play(0, 4)
                stage = 0 # reset
                dude.DigitalWrite(PORT.OUTPUT1, 1,1) #value 0-1
                time.sleep(1)
                dude.DigitalWrite(PORT.OUTPUT1, 1,0) #value 0-1
            print("----------")

            img.draw_string(2,2, ("%2.1f C" %(temperature)), color=(0,255,0), scale=4)
            time.sleep(sleep_between_person)


        if type(rx) == bytes  :

            if rx ==  b'body = ':
                body = 0
                some_bad_bytes = rx
                temp_text = str( some_bad_bytes )[3:-1]
                print("body body : ",temp_text)





        if rx != None :
            #print(rx,end='')

            thislist.append(rx)

            if rx[0] == 85 and rx[1] == 170 and rx[2] == 7 and rx[3] == 4 :
                temperature = int(struct.unpack("<H",rx[4:8])[0])/10

                if temperature < 37.5 :
                    #player.play(0, 3)
                    print ("Temperature : %2.1f",temperature)
                    stage = 0 # reset

                    dude.Servo(PORT.OUTPUT1,1,0)
                    time.sleep(2)
                    dude.Servo(PORT.OUTPUT1,1,90)
                    time.sleep(2)
                    dude.Servo(PORT.OUTPUT1,1,0)
                    time.sleep(2)
                elif temperature >= 37.5 :
                    #player.play(0, 4)
                    stage = 0 # reset
                print("----------")

                img.draw_string(2,2, ("%2.1f C" %(temperature)), color=(0,255,0), scale=4)
                time.sleep(sleep_between_person)
        else:

            print("No read temperature")
            print(thislist)
            textMeter = ""

            for i in range(len(thislist)):
              textMeter = textMeter+str(thislist[i])[0:-1]

            print(textMeter)

            text1 = textMeter.replace('b\'', '')
            text2 = text1.replace('\r\n','')
            list_text2 = text2.split()
            print(list_text2)

            text3 = ""
            temperature = 0.0
            for i in range(len(list_text2)):

                if list_text2[i] == "body":
                    print('Temperature')
                    print(list_text2[i+2])
                    tempSub = list_text2[i+2][0:5]
                    temperature = float(tempSub)



            if temperature >31.5 and temperature < 37.5 :

                print ("Temperature : %2.1f",temperature)
                stage = 0 # reset
                dude.Servo(PORT.OUTPUT1,1,0)
                time.sleep(0.1)
                dude.Servo(PORT.OUTPUT1,1,90)
                time.sleep(2)
                dude.Servo(PORT.OUTPUT1,1,0)
                time.sleep(1)
            elif temperature >= 37.5 :
                #player.play(0, 4)
                dude.DigitalWrite(PORT.OUTPUT1, 1,1) #value 0-1
                time.sleep(2)
                dude.DigitalWrite(PORT.OUTPUT1, 1,0) #value 0-1
                stage = 0 # reset
                print("----------HIGH----------")

            print("--------------------")

            img.draw_string(2,2, ("%2.1f C" %(temperature)), color=(0,255,0), scale=4)


            temperature = 0.0
            thislist = []
            #time.sleep(sleep_between_person)



        ######################################
        if time.ticks_ms() - timestamp > timeout_wait_check:
            stage = 0 # reset
            temperature = 0.0
    #--------------- End State ---------------------------

    print("Stage : %d , Timeout %d" %(stage,time.ticks_ms() - timestamp+1))
    dude.DigitalWrite(PORT.OUTPUT1, 1,0) #value 0-1

    a = lcd.display(img)

a = kpu.deinit(task)

