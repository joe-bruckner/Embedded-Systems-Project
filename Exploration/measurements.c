/*	----------------------------------------------------------------------
	measurements.c
	
	Functions to pipe and read internal processor status attributes on the 
	Raspberry Pi 4
	----------------------------------------------------------------------*/
	
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>

static float get_command_result(char* command);
int get_gpu_temp();
int get_cpu_temp();
int get_cpu_freq();
int get_cpu_volts();

/*	----------------------------------------------------------------------
	Send requested command and return result
	----------------------------------------------------------------------*/
static float get_command_result(char* command) {
	FILE *filept;
    char data[64];
	
    // Open pipe for reading and execute the command
    filept = popen(command,"r");

    // Get the data from the pipe
    fgets(data, 64, filept);
	
	// Close pipe
	assert(pclose(filept) == 0);
	
	// Convert to float
	float result = atof(data);
	assert(result >= 0);
	
	// Return as an integer
	return result;
}

/*	----------------------------------------------------------------------
	Retrieve the GPU temperature and return as an interger in celcius
	----------------------------------------------------------------------*/
int get_gpu_temp() {
    return (int)(get_command_result("vcgencmd measure_temp | sed 's/[^0-9.]//g'"));
}

/*	----------------------------------------------------------------------
	Retrieve the CPU temperature and return as an interger in celcius
	----------------------------------------------------------------------*/
int get_cpu_temp() {
    return (int)(get_command_result("cat /sys/class/thermal/thermal_zone0/temp")/1000);
}

/*	----------------------------------------------------------------------
	Retrieve the CPU operating frequency in hertz
	----------------------------------------------------------------------*/
int get_cpu_freq() {
    return (int)(get_command_result("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"));
}

/*	----------------------------------------------------------------------
	Retrieve the core operating voltage in millivolts
	----------------------------------------------------------------------*/
int get_cpu_volts() {
	return (int)(get_command_result("vcgencmd measure_volts | sed 's/[^0-9.]//g'")*1000);
}
