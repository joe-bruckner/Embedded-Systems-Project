#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/types.h>
#include <unistd.h> 
#include <assert.h>

#include "measurements.c"

int main() {	
	// Set filename
	char file[32] = "test";
	char filename[32];
	sprintf(filename, "%s.csv", file);
	
	// Append filename if it exists, then open file
	int  v = 0;
	while(access(filename, F_OK) != -1) {
		sprintf(filename, "%s_%d.csv", file, ++v);
	}
	FILE *filept = fopen(filename, "w");
	
	// Print file header
	fprintf(filept, "CPU Temp,GPU Temp,CPU Freq,CPU Volts,Runtime\n");
	
	for (int  i = 0; i < 2; i++) {
		// Record and check temperature
		int  cpu_t = get_cpu_temp();
		int  gpu_t = get_gpu_temp();
		assert((cpu_t > 0) && (cpu_t < 80) && (gpu_t > 0) && (gpu_t < 80));
		
		// Arithmetic and evaluation operations
		time_t run_s = time(NULL);
		for(int n = 0; n < 1000000000; n++) {
			int number = n/2;
			if(n == 2*number)
				number++;
		}
		time_t run_f = time(NULL);
		
		// Print results to file
		fprintf(filept, "%d,%d,%d,%d,%d\n", get_cpu_temp(), get_gpu_temp(), get_cpu_freq(), get_cpu_volts(), (run_f - run_s));
	}
	
	for (int  i = 0; i < 2; i++) {
		// Record and check temperature
		int  cpu_t = get_cpu_temp();
		int  gpu_t = get_gpu_temp();
		assert((cpu_t > 0) && (cpu_t < 80) && (gpu_t > 0) && (gpu_t < 80));
		
		// Print results to file
		fprintf(filept, "%d,%d,%d,%d,%d\n", get_cpu_temp(), get_gpu_temp(), get_cpu_freq(), get_cpu_volts(), 5);
		sleep(5);
	}
	
	// Close file
	assert(fclose(filept) == 0);
	
	return 0;
}
