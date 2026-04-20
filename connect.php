<?php
$studentemail = filter_input(INPUT_POST, 'studentemail', FILTER_SANITIZE_STRING);
$password = filter_input(INPUT_POST, 'password', FILTER_SANITIZE_STRING);

$host = "localhost";
$dbusername = "root";
$dbpassword = "";
$dbname = "sahabatmmu_2";

$conn = new mysqli($host, $dbusername, $dbpassword, $dbname);

if ($conn->connect_error) {
  die('Connect Error ('. $conn->connect_errno .') '.$conn->connect_error);
} else {
  $stmt = $conn->prepare("INSERT INTO accounts (studentemail, password) VALUES(?, ?)");

  if ($stmt === false) {
    die('Prepare failed: ' . $conn->error);
  }

  $stmt->bind_param("ss", $studentemail, $password);

  if ($stmt->execute()) {
    echo "You have succefully registered";
  } else {
    echo "Error; " . $stmt->error;
  }

  $stmt->close();
  $conn->close();
}
?>