#!/usr/bin/php
<?php

// Report all errors. Errors should never be ignored, it means that our
// application is broken and we need to fix it.
error_reporting(-1);

// Transform PHP's super weird error system to comprehensible exceptions.
set_error_handler(function($errno, $errstr, $errfile, $errline) {
    throw new ErrorException($errstr, 0, $errno, $errfile, $errline);
    // Don't execute PHP internal error handler.
    return true;
});


try {

//$radio = [
//    "802.11g/n (IAP)",
//    "802.11a/n (IAP)",
//];
$ip   = "IP";
$snmp = "SNMP"; // Keep this secret :)


$ssid = array();
//$radio = array();
$wlanTable = snmprealwalk($ip, $snmp, ".1.3.6.1.4.1.14823.2.3.3.1.2.3.1");
foreach ($wlanTable as $index => $value) {
    $index = str_replace("iso.3.6.1.4.1.14823.2.3.3.1.2.3.1.", "", $index);
    $index2 = explode(".", $index);
    $index3 = array();

    for ($i = 1; $i < 8; $i++) {
        $index3[] = $index2[$i];
    }
    $index3 = implode(".", $index3);

    if ($index2[0] == 4) {
        $mac = str_replace(" ",":", trim(str_replace("Hex-STRING: ", "", $value)));
        $ssid[$mac] = $wlanTable["iso.3.6.1.4.1.14823.2.3.3.1.2.3.1.3.".$index3];
//        $radio[$mac] = trim(str_replace("INTEGER: ", "", $wlanTable["iso.3.6.1.4.1.14823.2.3.3.1.2.3.1.2.".$index3]));
    }
}

$macs = array();
$clientTable = snmprealwalk($ip, $snmp, ".1.3.6.1.4.1.14823.2.3.3.1.2.4.1");
foreach($clientTable as $index => $value) {
    $index = str_replace("iso.3.6.1.4.1.14823.2.3.3.1.2.4.1.", "", $index);
    $index2 = explode(".", $index);
    $index3 = array();

    for ($i = 1; $i <= 6; $i++) {
        $index3[] = $index2[$i];
    }
    $index3 = implode(".", $index3);

    if ($index2[0] == 1) {
        $radio_mac = $clientTable["iso.3.6.1.4.1.14823.2.3.3.1.2.4.1.2.".$index3];
        $username  = $clientTable["iso.3.6.1.4.1.14823.2.3.3.1.2.4.1.5.".$index3];
        // Only count the username field an actual username if it contains an '@'.
        $username  = strpos($username, "@") !== false ? $username : "";
        $radio_mac = str_replace(" ", ":", trim(str_replace("Hex-STRING: ", "", $radio_mac)));
        $macs[] = array (
            "mac"      => strtolower(str_replace(" ", ":", trim(str_replace("Hex-STRING: ", "", $value)))),
            "ssid"     => trim(str_replace("\"", "", str_replace("STRING: ", "", $ssid[$radio_mac]))),
            "username" => $username !== "" ? trim(str_replace("\"", "", str_replace("STRING: ", "", $username))) : NULL,
            "signal"   => intval(trim(str_replace("INTEGER: ", "", $clientTable["iso.3.6.1.4.1.14823.2.3.3.1.2.4.1.7.".$index3]))),
        );
    }
}

print(json_encode($macs, JSON_PRETTY_PRINT)."\n");

} catch (Exception $err) {
    print("Ah, fuck: $err\n");
}
