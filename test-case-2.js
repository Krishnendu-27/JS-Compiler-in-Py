// =====================================
// MODIFIED TEST SUITE
// =====================================

// ---------- TC1: Odd / Even ----------
console.log("=== TC1 ===");

let num = 12;

if (num % 2 === 0) {
  console.log(num + " is Even");
} else {
  console.log(num + " is Odd");
}

// ---------- TC2: Triangle Pattern ----------
console.log("=== TC2 ===");

for (let i = 1; i <= 4; i++) {
  let row = "";

  for (let j = 1; j <= i; j++) {
    row += "#";
  }

  console.log(row);
}

// ---------- TC3: Armstrong ----------
console.log("=== TC3 ===");

function isArmstrong(num) {
  let temp = num;
  let sum = 0;

  while (temp > 0) {
    let digit = temp % 10;
    sum += digit ** 3;
    temp = Math.floor(temp / 10);
  }

  return sum === num;
}

console.log(isArmstrong(370));
console.log(isArmstrong(200));

// ---------- TC4: Array Reverse ----------
console.log("=== TC4 ===");

let arr = [10, 20, 30, 40];
let reversed = [...arr].reverse();

console.log("Original:", arr);
console.log("Reversed:", reversed);

// ---------- TC5: Palindrome ----------
console.log("=== TC5 ===");

let str = "madam";
let reversedStr = str.split("").reverse().join("");

console.log(
  str === reversedStr ? str + " is a Palindrome" : str + " is not a Palindrome",
);

// =====================================
// VARIABLES
// =====================================

console.log("=== VARIABLES ===");

let a = 50;
const b = 100;

console.log(a);
console.log(b);

a = 75;
console.log(a);

// =====================================
// IF ELSE
// =====================================

console.log("=== IF ELSE ===");

let score = 92;

if (score >= 90) {
  console.log("A");
} else if (score >= 70) {
  console.log("B");
} else {
  console.log("C");
}

// =====================================
// SWITCH
// =====================================

console.log("=== SWITCH ===");

let day = 5;

switch (day) {
  case 1:
    console.log("Mon");
    break;
  case 2:
    console.log("Tue");
    break;
  case 5:
    console.log("Fri");
    break;
  default:
    console.log("Unknown");
}

// =====================================
// ARRAYS
// =====================================

console.log("=== ARRAYS ===");

let nums = [5, 10, 15];

nums.push(20);
console.log(nums);

nums.pop();
console.log(nums);

// =====================================
// ARRAY METHODS
// =====================================

console.log("=== ARRAY METHODS ===");

let values = [2, 4, 6, 8];

console.log(values.map((x) => x + 1));
console.log(values.filter((x) => x > 4));
console.log(values.reduce((sum, x) => sum + x, 0));

// =====================================
// STRINGS
// =====================================

console.log("=== STRINGS ===");

let text = "JavaScript";

console.log(text.toUpperCase());
console.log(text.toLowerCase());
console.log(text.includes("Script"));

// =====================================
// OBJECTS
// =====================================

console.log("=== OBJECTS ===");

let person = {
  name: "Alice",
  age: 30,
};

console.log(person.name);
console.log(person.age);

// =====================================
// RECURSION
// =====================================

console.log("=== RECURSION ===");

function factorial(n) {
  if (n <= 1) return 1;
  return n * factorial(n - 1);
}

console.log(factorial(6));

// =====================================
// END
// =====================================

console.log("ALL TESTS COMPLETED");
