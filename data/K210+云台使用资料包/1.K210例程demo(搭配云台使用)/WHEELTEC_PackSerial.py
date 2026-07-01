import struct

"""
将需要发送的数据打包 类
"""
class Uart_RecvPack():
    def __init__(self,packmsg,dataformat):

        # 传输的数据包
        self.msg = packmsg

        # 传输的数据格式
        self.recvformat = dataformat

        # 要传输的数据长度
        self.data_len = struct.calcsize(self.recvformat)

    # BCC校验函数
    def calculate_BCC(self,datalist,datalen):
        ref = 0
        for i in range(datalen):
            ref = (ref^datalist[i])
        return ref&0xff

    # 接收读取到的数据列表并解包
    def unpack_value(self,datalist):
        try:
            bccref = self.calculate_BCC( datalist , self.data_len-2 )
            if bccref == datalist[self.data_len-2]:
                tmpmsg = bytes(datalist)
                tmpmsg = struct.unpack(self.recvformat,tmpmsg)
                self.msg.update( zip(self.msg.keys(),tmpmsg ) )
            else:
                return False
        except Exception as e:
            return False

        return True

"""
将需要接收的数据解包 类
"""
class Uart_SendPack():
    def __init__(self,packmsg,dataformat):

        # 传输的数据包
        self.msg = packmsg

        # 传输的数据格式
        self.sendformat = dataformat

        # 要传输的数据长度
        self.data_len = struct.calcsize(self.sendformat)


    # BCC校验函数
    def calculate_BCC(self,datalist,datalen):
        ref = 0
        for i in range(datalen):
            ref = (ref^datalist[i])
        return ref&0xff

    # 将要打包的数据进行BCC校验,并返回最终BCC校验的值
    def pack_BCC_Value(self):
        tmp_list = list( self.msg.values() ) # 将字典的值取出转换成列表

        tmp_packed = struct.pack(self.sendformat,*tmp_list) # 根据指定的数据类型对列表值进行自动打包

        # 自动打包后的数值，进行BCC校验，获得最终需要发送的BCC校验值
        return self.calculate_BCC(tmp_packed,len(tmp_packed)-2)

    # 获取最终要发送的数据列表
    def get_Pack_List(self):
        tmplist = list(self.msg.values())# 将字典的值取出,转换成列表
        return struct.pack(self.sendformat,*tmplist)