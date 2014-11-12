#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>


void sleep_nanos(long nanos) {
    struct timespec rqtp;
    rqtp.tv_sec = 0;
    rqtp.tv_nsec = nanos;
    nanosleep(&rqtp, NULL);
}

long get_time_nanos() {
    struct timeval t;
    gettimeofday(&t, NULL);
    return t.tv_sec * 1000000000L + t.tv_usec * 1000;
}

char* read_file(char* filename) {
    static char buf[32768];

    size_t pos = 0;
    int fd = open(filename, 0);

    for (;;) {
        ssize_t result = read(fd, buf+pos, sizeof(buf)-pos);
        if (result < 0) {
            fprintf(stderr, "Failed reading file: %s -- %s\n", strerror(errno), filename);
            return NULL;
        }
        if (result == 0) {
            return buf;
        }
        pos += result;
        if (pos >= sizeof(buf)) {
            fprintf(stderr, "Failed reading file, too much data: %s\n", filename);
            return buf;
        }
    }
}

int parse_int(char* s) {
    if (s == NULL) {
        return -1;
    }

    errno = 0;
    int value = strtol(s, NULL, 10);
    if (errno != 0) {
        fprintf(stderr, "Failed to parse string: %s -- %s\n", strerror(errno), s);
        return -1;
    }

    return value;
}

char* read_next_line(char** s) {
    char* end = index(*s, '\n');
    if (end == NULL) {
        return NULL;
    }

    char* line = *s;
    *s = end+1;
    *end = '\0';
    return line;
}

int read_cpu_idle_jiffys() {
    char* procstat = read_file("/proc/stat");
    if (procstat == NULL) {
        return -1;
    }

    char* line = read_next_line(&procstat);
    if (line == NULL) {
        return -1;
    }

    char* result = NULL;
    for (int i = 0; i <= 4; ++i, line=NULL) {
        result = strtok(line, " ");
    }
    return parse_int(result);
}

int count_cpus() {
    char* procstat = read_file("/proc/stat");
    if (procstat == NULL) {
        return -1;
    }

    int count = -1;
    while (*procstat) {
        char* line = read_next_line(&procstat);
        if (line == NULL) {
            break;
        }
        if (strncmp("cpu", line, 3) == 0) {
            ++count;
        }
    }
    return count;
}

int read_cpu_percent() {
    int num_cpus = count_cpus();

    long tstart = get_time_nanos();
    int idle_jiffy1 = read_cpu_idle_jiffys();
    sleep_nanos(100000000L);
    int idle_jiffy2 = read_cpu_idle_jiffys();
    long tend = get_time_nanos();

    double duration_sec = ((double)tend - (double)tstart) / 1000000000.0;
    double idle_jiffys_per_second = (idle_jiffy2 - idle_jiffy1) / duration_sec;

    double idle_jiffys_per_cpu_second = idle_jiffys_per_second / num_cpus;

    // One jiffy is 10ms, so we can get the percentage very easily!
    return 100 - (int)round(idle_jiffys_per_cpu_second);
}

int read_mem_percent() {
    char* meminfo = read_file("/proc/meminfo");
    if (meminfo == NULL) {
        return -1;
    }

    int mem_total = -1;
    int mem_free = -1;

    while (*meminfo && (mem_total < 0 || mem_free < 0)) {
        char* line = read_next_line(&meminfo);
        if (line == NULL) {
            break;
        }

        char* key = strtok(line, ": ");
        char* value_str = strtok(NULL, ": ");

        if (key == NULL || value_str == NULL) {
            fprintf(stderr, "Failed to parse key/value token in /proc/meminfo\n");
            return -1;
        }

        if (strcmp(key, "MemTotal") == 0) {
            mem_total = parse_int(value_str);
        } else if (strcmp(key, "MemAvailable") == 0) {
            mem_free = parse_int(value_str);
        }
    }

    if (mem_total < 0 || mem_free < 0) {
        fprintf(stderr, "Failed to find MemTotal and MemAvailable in /proc/meminfo\n");
        return -1;
    }

    int mem_used = mem_total - mem_free;

    return (int)round((double)mem_used / (double)mem_total * 100);
}

int read_battery_percent() {
    char* percent_str = NULL;
    for (int i = 0; i <= 1 && percent_str == NULL; ++i) {
        percent_str = read_file("/sys/class/power_supply/BAT1/capacity");
    }
    return parse_int(percent_str);
}

void print_percent(
    char* name, char* units,
    int value,
    int red_low, int red_high
) {
    if (value < 0) {
        return;
    }

    char* color = "black";
    if (value >= red_low && value <= red_high) {
        color = "red";
    }

    printf(
        "%s <span color='%s'>%d</span>%s  ",
        name, color, value, units
    );
}

int main(void) {
    printf("<txt>");

    print_percent(
        "cpu", "%",
        read_cpu_percent(),
        50, 100
    );

    print_percent(
        "mem", "%",
        read_mem_percent(),
        70, 100
    );

    print_percent(
        "batt", "%",
        read_battery_percent(),
        0, 25
    );

    printf("</txt>");

    return 0;
}
