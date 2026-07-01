#ifndef __SERVO_H
#define __SERVO_H

#include <stdint.h>

//ÔÆÌ¨ÖÐÖµ
#define PTZ_MIDDLE 750

void TIM4_PWM_Init(uint16_t arr,uint16_t psc);

#endif /* __SERVO_H */
