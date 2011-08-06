#!/usr/bin/env ruby

# # Sample config file
# ROOTCA = "/etc/ssl/certs/ca-certificates.crt"
# SMTPSERVER = "mail.example.com"
# FROMADDR = "cron@example.com"
# SLEEPTIME = 15
# ACCOUNTS = [
#	["person1@example.com", "0499999999", "000000", 100, 30],
#	["person2@example.com", "0499999998", "000000", 100, 30],
# ]

require 'optparse'
require 'net/http'
require 'net/https'
require 'net/smtp'
require 'uri'

class VirginMobile
	def initialize(sleep_time, username, password)
		@sleep_time = sleep_time
		@username = username
		@password = password
		@cookie = nil
	end

	def do_request(path, form_data=nil)
		sleep(@sleep_time) # Don't look like a bot
		http = Net::HTTP.new("www.virginmobile.com.au", 443)
		http.use_ssl = true
		if File.exist? ROOTCA
			http.ca_file = ROOTCA
			http.verify_mode = OpenSSL::SSL::VERIFY_PEER
			http.verify_depth = 5
		end
		if @cookie
			req = Net::HTTP::Get.new(path)
			req["Cookie"] = @cookie
		end
		if form_data
			req = Net::HTTP::Post.new(path)
			req.form_data = form_data
		end
		return http.request(req)
	end

	def do_login
		form_data = {
			"username" => @username,
			"password" => @password,
		}
		res = do_request("/selfcare/MyAccount/LogoutLoginPre.jsp", form_data)
		@cookie = res.fetch("Set-Cookie")

		while location = res.get_fields("Location")
			location = URI.parse(location[0])
			res = do_request(location.path)
		end
	end

	def do_logout
		do_request("/selfcare/dispatch/Logout")
	end

	def request_bill_preview
		res = do_request("/selfcare/dispatch/PostPayUnbilledUsage")
		usage = res.body.scan(/\$([\d\.]+)/).flatten
		last_bill_date = res.body.gsub(/\n/, '').scan(/Last bill date:.*>(\d\d?\/\d\d?\/\d\d\d\d)/).flatten
		return usage, last_bill_date
	end

	def request_mobile_browsing
		res = do_request("/selfcare/dispatch/DataUsageRequest")
		data_usage = res.body.gsub(/\n/, '').scan(/Data used this billing month:.*>(\d+) MB \(/).flatten
		return data_usage
	end

	def dump_result(res)
		res.each_capitalized do |key, value|
			print "#{key}: #{value}\n"
		end
		print res.body + "\n"
	end
end

def check_usage(sleep_time, ignore_limits, destination, username, password, usageLimit, dataLimit)
	message = ""
	data = VirginMobile.new(sleep_time, username, password)
	data.do_login

	usage, last_bill_date = data.request_bill_preview
	usage.each do |x|
		if ignore_limits or (usageLimit >= 0 and x.to_f >= usageLimit)
			message += "Unbilled usage: $#{x}\n"
		end
	end

	data_usage = data.request_mobile_browsing
	data_usage.each do |x|
		if ignore_limits or (dataLimit >= 0 and x.to_f >= dataLimit)
			message += "Data usage: #{x} MiB\n"
		end
	end

	data.do_logout

	if message.length > 0
		return destination, <<EOT
From: #{FROMADDR}
To: #{destination}
Subject: Virgin Mobile Usage

Virgin Mobile Usage
-------------------

Previous bill: #{last_bill_date}
#{message}

https://www.virginmobile.com.au/selfcare/MyAccount/login.jsp

EOT

	end
end

def send_emails(emails)
	Net::SMTP.start(SMTPSERVER, 25) do |smtp|
		emails.each do |destination, message|
			smtp.send_message(message, FROMADDR, destination)
		end
	end
end

def do_email(sleep_time, ignore_limits)
	emails = []
	ACCOUNTS.each do |args|
		if ret = check_usage(sleep_time, ignore_limits, *args)
			emails.push(ret)
		end
	end
	send_emails(emails)
end

def do_print(sleep_time, ignore_limits)
	emails = []
	ACCOUNTS.each do |args|
		if ret = check_usage(sleep_time, ignore_limits, *args)
			print ret[1]
		end
	end
end

def main
	ignore_limits = dry_run = fast = false
	OptionParser.new do |opts|
		opts.banner = "Usage: #{$0} [options] config\n"
		opts.on("--fast", "Don't sleep between connections") do |v|
			fast = v
		end
		opts.on("--dry-run", "Don't send emails, just print them") do |v|
			dry_run = v
		end
		opts.on("--ignore-limits", "Treat all limits as 0") do |v|
			ignore_limits = v
		end
	end.parse!

	config = ARGV[0]
	begin
		eval File.open(config).read
	rescue
		$stderr.print "Error parsing config file!\n\n"
		raise
	end

	if fast
		sleep_time = 0
	else
		sleep_time = SLEEPTIME
	end

	if dry_run
		do_print(sleep_time, ignore_limits)
	else
		do_email(sleep_time, ignore_limits)
	end
end

if __FILE__ == $0
	main
end

