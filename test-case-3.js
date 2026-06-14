// Test Case 1: Odd / Even
let num = 25;

if (num % 2 === 0) {
  console.log(num + " is Even");
} else {
  console.log(num + " is Odd");
}

// Test Case 2: Pattern
for (let i = 1; i <= 6; i++) {
  let row = "";

  for (let j = 1; j <= i; j++) {
    row += "@";
  }

  console.log(row);
}

// Test Case 3: Array Reverse
let arr = [11, 22, 33, 44, 55];
let reversed = [...arr].reverse();

console.log("Original:", arr);
console.log("Reversed:", reversed);

// Test Case 4: Palindrome
let str = "level";
let reversedStr = str.split("").reverse().join("");

if (str === reversedStr) {
  console.log(str + " is a Palindrome");
} else {
  console.log(str + " is not a Palindrome");
}

// Variables
let a = 15;
const b = 45;

console.log(a);
console.log(b);

a = 60;
console.log(a);

// Grade Check
let score = 88;

if (score >= 90) {
  console.log("A");
} else if (score >= 70) {
  console.log("B");
} else {
  console.log("C");
}

// Switch
let day = 1;

switch (day) {
  case 1:
    console.log("Mon");
    break;
  case 2:
    console.log("Tue");
    break;
  default:
    console.log("Unknown");
}

// Arrays
let nums = [2, 4, 6];

nums.push(8);
console.log(nums);

nums.pop();
console.log(nums);

// Array Methods
let values = [3, 6, 9, 12];

console.log(values.map((x) => x * 3));
console.log(values.filter((x) => x > 5));
console.log(values.reduce((sum, x) => sum + x, 0));

// Strings
let text = "Programming";

console.log(text.toUpperCase());
console.log(text.toLowerCase());
console.log(text.includes("gram"));

// Objects
let person = {
  name: "Bob",
  age: 28,
};

console.log(person.name);
console.log(person.age);

// Recursion
function factorial(n) {
  if (n <= 1) return 1;
  return n * factorial(n - 1);
}

console.log(factorial(4));

console.log("TESTS COMPLETED");
