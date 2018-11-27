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

    if (fd < 0) {
        return NULL;
    }

    for (;;) {
        ssize_t result = read(fd, buf+pos, sizeof(buf)-pos);
        if (result < 0) {
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

long parse_int(char* s) {
    if (s == NULL) {
        return -1;
    }

    errno = 0;
    long value = strtol(s, NULL, 10);
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
        fprintf(stderr, "Failed reading file /proc/stat: %s\n", strerror(errno));
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
        fprintf(stderr, "Failed reading file /proc/stat: %s\n", strerror(errno));
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

int read_meminfo(int* mem_free_mibis, int* mem_total_mibis) {
    char* meminfo = read_file("/proc/meminfo");
    if (meminfo == NULL) {
        fprintf(stderr, "Failed reading file /proc/meminfo: %s\n", strerror(errno));
        return -1;
    }

    *mem_free_mibis = -1;
    *mem_total_mibis = -1;

    while (*meminfo) {
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

        if (strcmp(key, "MemAvailable") == 0) {
            int mem_available = parse_int(value_str);
            *mem_free_mibis = (int)round((double)mem_available / 1024);
        }

        if (strcmp(key, "MemTotal") == 0) {
            int mem_available = parse_int(value_str);
            *mem_total_mibis = (int)round((double)mem_available / 1024);
        }
    }

    if (*mem_free_mibis < 0 || *mem_total_mibis < 0) {
        fprintf(stderr, "Failed to find field in /proc/meminfo\n");
        return -1;
    } else {
        return 0;
    }
}

int read_zfs_arc_used_mibis() {
    char* arcstats = read_file("/proc/spl/kstat/zfs/arcstats");
    if (arcstats == NULL) {
        return -1;
    }

    while (*arcstats) {
        char* line = read_next_line(&arcstats);
        if (line == NULL) {
            break;
        }

        char* key = strtok(line, " ");
        strtok(NULL, " ");
        char* value_str = strtok(NULL, " ");

        if (key == NULL || value_str == NULL) {
            fprintf(stderr, "Failed to parse key/value token in /proc/spl/kstat/zfs/arcstats\n");
            return -1;
        }

        if (strcmp(key, "size") == 0) {
            long arc_used = parse_int(value_str);
            return (int)round((double)arc_used / 1024 / 1024);
        }
    }

    fprintf(stderr, "Failed to find 'c' in /proc/spl/kstat/zfs/arcstats\n");
    return -1;
}

int read_battery_percent() {
    char* percent_str = NULL;

    if (percent_str == NULL) {
        percent_str = read_file("/sys/class/power_supply/BAT0/capacity");
    }

    if (percent_str == NULL) {
        percent_str = read_file("/sys/class/power_supply/BAT1/capacity");
    }

    if (percent_str == NULL) {
        fprintf(stderr, "Failed reading file battery capacity file: %s\n", strerror(errno));
        return -1;
    }

    return parse_int(percent_str);
}

void print_red_threshold(
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
        "%s <span color='%s'>%d</span>%s\n",
        name, color, value, units
    );
}

int main(int argc, char** argv) {
    char* show_flags = "cmb";
    char* top_padding = "0";
    if (argc >= 2) {
        show_flags = argv[1];
    }
    if (argc >= 3) {
        top_padding = argv[2];
    }

    printf("<txt><span size=\"%s\">\n</span>", top_padding);

    if (strchr(show_flags, 'c')) {
        print_red_threshold(
            "cpu", "%",
            read_cpu_percent(),
            50, 100
        );
    }

    if (strchr(show_flags, 'm')) {
        int mem_free_mibis, mem_total_mibis;
        read_meminfo(&mem_free_mibis, &mem_total_mibis);
        print_red_threshold(
            "mem", " MiB",
            mem_free_mibis + read_zfs_arc_used_mibis(),
            0, mem_total_mibis / 10
        );
    }

    if (strchr(show_flags, 'b')) {
        print_red_threshold(
            "batt", "%",
            read_battery_percent(),
            0, 25
        );
    }

    printf("</txt>");

    return 0;
}
