import {
  AMPLIFY_SYMBOL,
  Amplify,
  AmplifyError,
  AmplifyUrl,
  AmplifyUrlSearchParams,
  ApiAction,
  ApiError,
  Category,
  ConsoleLogger,
  Hub,
  NonRetryableError,
  Observable,
  Reachability,
  USER_AGENT_HEADER,
  amplifyUuid,
  base64Encoder,
  catchError,
  composeTransferHandler,
  fetchAuthSession,
  fetchTransferHandler,
  filter,
  getAmplifyUserAgent,
  getRetryDecider,
  isNonRetryableError,
  jitteredBackoff,
  jitteredExponentialRetry,
  map,
  parseJsonError,
  retryMiddlewareFactory,
  signRequest,
  signingMiddlewareFactory,
  userAgentMiddlewareFactory
} from "./chunk-UFPSZHE6.js";
import {
  __export
} from "./chunk-G3PMV62Z.js";

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/version.mjs
var versionInfo = Object.freeze({
  major: 15,
  minor: 8,
  patch: 0,
  preReleaseTag: null
});

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/isObjectLike.mjs
function _typeof(obj) {
  "@babel/helpers - typeof";
  if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") {
    _typeof = function _typeof6(obj2) {
      return typeof obj2;
    };
  } else {
    _typeof = function _typeof6(obj2) {
      return obj2 && typeof Symbol === "function" && obj2.constructor === Symbol && obj2 !== Symbol.prototype ? "symbol" : typeof obj2;
    };
  }
  return _typeof(obj);
}
function isObjectLike(value) {
  return _typeof(value) == "object" && value !== null;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/polyfills/symbols.mjs
var SYMBOL_ITERATOR = typeof Symbol === "function" && Symbol.iterator != null ? Symbol.iterator : "@@iterator";
var SYMBOL_ASYNC_ITERATOR = typeof Symbol === "function" && Symbol.asyncIterator != null ? Symbol.asyncIterator : "@@asyncIterator";
var SYMBOL_TO_STRING_TAG = typeof Symbol === "function" && Symbol.toStringTag != null ? Symbol.toStringTag : "@@toStringTag";

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/location.mjs
function getLocation(source, position) {
  var lineRegexp = /\r\n|[\n\r]/g;
  var line = 1;
  var column = position + 1;
  var match;
  while ((match = lineRegexp.exec(source.body)) && match.index < position) {
    line += 1;
    column = position + 1 - (match.index + match[0].length);
  }
  return {
    line,
    column
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/printLocation.mjs
function printLocation(location2) {
  return printSourceLocation(location2.source, getLocation(location2.source, location2.start));
}
function printSourceLocation(source, sourceLocation) {
  var firstLineColumnOffset = source.locationOffset.column - 1;
  var body = whitespace(firstLineColumnOffset) + source.body;
  var lineIndex = sourceLocation.line - 1;
  var lineOffset = source.locationOffset.line - 1;
  var lineNum = sourceLocation.line + lineOffset;
  var columnOffset = sourceLocation.line === 1 ? firstLineColumnOffset : 0;
  var columnNum = sourceLocation.column + columnOffset;
  var locationStr = "".concat(source.name, ":").concat(lineNum, ":").concat(columnNum, "\n");
  var lines = body.split(/\r\n|[\n\r]/g);
  var locationLine = lines[lineIndex];
  if (locationLine.length > 120) {
    var subLineIndex = Math.floor(columnNum / 80);
    var subLineColumnNum = columnNum % 80;
    var subLines = [];
    for (var i = 0; i < locationLine.length; i += 80) {
      subLines.push(locationLine.slice(i, i + 80));
    }
    return locationStr + printPrefixedLines([["".concat(lineNum), subLines[0]]].concat(subLines.slice(1, subLineIndex + 1).map(function(subLine) {
      return ["", subLine];
    }), [[" ", whitespace(subLineColumnNum - 1) + "^"], ["", subLines[subLineIndex + 1]]]));
  }
  return locationStr + printPrefixedLines([
    // Lines specified like this: ["prefix", "string"],
    ["".concat(lineNum - 1), lines[lineIndex - 1]],
    ["".concat(lineNum), locationLine],
    ["", whitespace(columnNum - 1) + "^"],
    ["".concat(lineNum + 1), lines[lineIndex + 1]]
  ]);
}
function printPrefixedLines(lines) {
  var existingLines = lines.filter(function(_ref) {
    var _ = _ref[0], line = _ref[1];
    return line !== void 0;
  });
  var padLen = Math.max.apply(Math, existingLines.map(function(_ref2) {
    var prefix = _ref2[0];
    return prefix.length;
  }));
  return existingLines.map(function(_ref3) {
    var prefix = _ref3[0], line = _ref3[1];
    return leftPad(padLen, prefix) + (line ? " | " + line : " |");
  }).join("\n");
}
function whitespace(len) {
  return Array(len + 1).join(" ");
}
function leftPad(len, str) {
  return whitespace(len - str.length) + str;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/error/GraphQLError.mjs
function _typeof2(obj) {
  "@babel/helpers - typeof";
  if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") {
    _typeof2 = function _typeof6(obj2) {
      return typeof obj2;
    };
  } else {
    _typeof2 = function _typeof6(obj2) {
      return obj2 && typeof Symbol === "function" && obj2.constructor === Symbol && obj2 !== Symbol.prototype ? "symbol" : typeof obj2;
    };
  }
  return _typeof2(obj);
}
function ownKeys(object, enumerableOnly) {
  var keys = Object.keys(object);
  if (Object.getOwnPropertySymbols) {
    var symbols = Object.getOwnPropertySymbols(object);
    if (enumerableOnly) symbols = symbols.filter(function(sym) {
      return Object.getOwnPropertyDescriptor(object, sym).enumerable;
    });
    keys.push.apply(keys, symbols);
  }
  return keys;
}
function _objectSpread(target) {
  for (var i = 1; i < arguments.length; i++) {
    var source = arguments[i] != null ? arguments[i] : {};
    if (i % 2) {
      ownKeys(Object(source), true).forEach(function(key) {
        _defineProperty(target, key, source[key]);
      });
    } else if (Object.getOwnPropertyDescriptors) {
      Object.defineProperties(target, Object.getOwnPropertyDescriptors(source));
    } else {
      ownKeys(Object(source)).forEach(function(key) {
        Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
      });
    }
  }
  return target;
}
function _defineProperty(obj, key, value) {
  if (key in obj) {
    Object.defineProperty(obj, key, { value, enumerable: true, configurable: true, writable: true });
  } else {
    obj[key] = value;
  }
  return obj;
}
function _classCallCheck(instance, Constructor) {
  if (!(instance instanceof Constructor)) {
    throw new TypeError("Cannot call a class as a function");
  }
}
function _defineProperties(target, props) {
  for (var i = 0; i < props.length; i++) {
    var descriptor = props[i];
    descriptor.enumerable = descriptor.enumerable || false;
    descriptor.configurable = true;
    if ("value" in descriptor) descriptor.writable = true;
    Object.defineProperty(target, descriptor.key, descriptor);
  }
}
function _createClass(Constructor, protoProps, staticProps) {
  if (protoProps) _defineProperties(Constructor.prototype, protoProps);
  if (staticProps) _defineProperties(Constructor, staticProps);
  return Constructor;
}
function _inherits(subClass, superClass) {
  if (typeof superClass !== "function" && superClass !== null) {
    throw new TypeError("Super expression must either be null or a function");
  }
  subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } });
  if (superClass) _setPrototypeOf(subClass, superClass);
}
function _createSuper(Derived) {
  var hasNativeReflectConstruct = _isNativeReflectConstruct();
  return function _createSuperInternal() {
    var Super = _getPrototypeOf(Derived), result;
    if (hasNativeReflectConstruct) {
      var NewTarget = _getPrototypeOf(this).constructor;
      result = Reflect.construct(Super, arguments, NewTarget);
    } else {
      result = Super.apply(this, arguments);
    }
    return _possibleConstructorReturn(this, result);
  };
}
function _possibleConstructorReturn(self, call) {
  if (call && (_typeof2(call) === "object" || typeof call === "function")) {
    return call;
  }
  return _assertThisInitialized(self);
}
function _assertThisInitialized(self) {
  if (self === void 0) {
    throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
  }
  return self;
}
function _wrapNativeSuper(Class) {
  var _cache = typeof Map === "function" ? /* @__PURE__ */ new Map() : void 0;
  _wrapNativeSuper = function _wrapNativeSuper2(Class2) {
    if (Class2 === null || !_isNativeFunction(Class2)) return Class2;
    if (typeof Class2 !== "function") {
      throw new TypeError("Super expression must either be null or a function");
    }
    if (typeof _cache !== "undefined") {
      if (_cache.has(Class2)) return _cache.get(Class2);
      _cache.set(Class2, Wrapper);
    }
    function Wrapper() {
      return _construct(Class2, arguments, _getPrototypeOf(this).constructor);
    }
    Wrapper.prototype = Object.create(Class2.prototype, { constructor: { value: Wrapper, enumerable: false, writable: true, configurable: true } });
    return _setPrototypeOf(Wrapper, Class2);
  };
  return _wrapNativeSuper(Class);
}
function _construct(Parent, args, Class) {
  if (_isNativeReflectConstruct()) {
    _construct = Reflect.construct;
  } else {
    _construct = function _construct2(Parent2, args2, Class2) {
      var a = [null];
      a.push.apply(a, args2);
      var Constructor = Function.bind.apply(Parent2, a);
      var instance = new Constructor();
      if (Class2) _setPrototypeOf(instance, Class2.prototype);
      return instance;
    };
  }
  return _construct.apply(null, arguments);
}
function _isNativeReflectConstruct() {
  if (typeof Reflect === "undefined" || !Reflect.construct) return false;
  if (Reflect.construct.sham) return false;
  if (typeof Proxy === "function") return true;
  try {
    Date.prototype.toString.call(Reflect.construct(Date, [], function() {
    }));
    return true;
  } catch (e) {
    return false;
  }
}
function _isNativeFunction(fn) {
  return Function.toString.call(fn).indexOf("[native code]") !== -1;
}
function _setPrototypeOf(o, p) {
  _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf2(o2, p2) {
    o2.__proto__ = p2;
    return o2;
  };
  return _setPrototypeOf(o, p);
}
function _getPrototypeOf(o) {
  _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf2(o2) {
    return o2.__proto__ || Object.getPrototypeOf(o2);
  };
  return _getPrototypeOf(o);
}
var GraphQLError = function(_Error) {
  _inherits(GraphQLError2, _Error);
  var _super = _createSuper(GraphQLError2);
  function GraphQLError2(message, nodes, source, positions, path, originalError, extensions) {
    var _nodeLocations, _nodeLocations2, _nodeLocations3;
    var _this;
    _classCallCheck(this, GraphQLError2);
    _this = _super.call(this, message);
    _this.name = "GraphQLError";
    _this.originalError = originalError !== null && originalError !== void 0 ? originalError : void 0;
    _this.nodes = undefinedIfEmpty(Array.isArray(nodes) ? nodes : nodes ? [nodes] : void 0);
    var nodeLocations = [];
    for (var _i2 = 0, _ref3 = (_this$nodes = _this.nodes) !== null && _this$nodes !== void 0 ? _this$nodes : []; _i2 < _ref3.length; _i2++) {
      var _this$nodes;
      var _ref4 = _ref3[_i2];
      var loc = _ref4.loc;
      if (loc != null) {
        nodeLocations.push(loc);
      }
    }
    nodeLocations = undefinedIfEmpty(nodeLocations);
    _this.source = source !== null && source !== void 0 ? source : (_nodeLocations = nodeLocations) === null || _nodeLocations === void 0 ? void 0 : _nodeLocations[0].source;
    _this.positions = positions !== null && positions !== void 0 ? positions : (_nodeLocations2 = nodeLocations) === null || _nodeLocations2 === void 0 ? void 0 : _nodeLocations2.map(function(loc2) {
      return loc2.start;
    });
    _this.locations = positions && source ? positions.map(function(pos) {
      return getLocation(source, pos);
    }) : (_nodeLocations3 = nodeLocations) === null || _nodeLocations3 === void 0 ? void 0 : _nodeLocations3.map(function(loc2) {
      return getLocation(loc2.source, loc2.start);
    });
    _this.path = path !== null && path !== void 0 ? path : void 0;
    var originalExtensions = originalError === null || originalError === void 0 ? void 0 : originalError.extensions;
    if (extensions == null && isObjectLike(originalExtensions)) {
      _this.extensions = _objectSpread({}, originalExtensions);
    } else {
      _this.extensions = extensions !== null && extensions !== void 0 ? extensions : {};
    }
    Object.defineProperties(_assertThisInitialized(_this), {
      message: {
        enumerable: true
      },
      locations: {
        enumerable: _this.locations != null
      },
      path: {
        enumerable: _this.path != null
      },
      extensions: {
        enumerable: _this.extensions != null && Object.keys(_this.extensions).length > 0
      },
      name: {
        enumerable: false
      },
      nodes: {
        enumerable: false
      },
      source: {
        enumerable: false
      },
      positions: {
        enumerable: false
      },
      originalError: {
        enumerable: false
      }
    });
    if (originalError !== null && originalError !== void 0 && originalError.stack) {
      Object.defineProperty(_assertThisInitialized(_this), "stack", {
        value: originalError.stack,
        writable: true,
        configurable: true
      });
      return _possibleConstructorReturn(_this);
    }
    if (Error.captureStackTrace) {
      Error.captureStackTrace(_assertThisInitialized(_this), GraphQLError2);
    } else {
      Object.defineProperty(_assertThisInitialized(_this), "stack", {
        value: Error().stack,
        writable: true,
        configurable: true
      });
    }
    return _this;
  }
  _createClass(GraphQLError2, [{
    key: "toString",
    value: function toString3() {
      return printError(this);
    }
    // FIXME: workaround to not break chai comparisons, should be remove in v16
    // $FlowFixMe[unsupported-syntax] Flow doesn't support computed properties yet
  }, {
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "Object";
    }
  }]);
  return GraphQLError2;
}(_wrapNativeSuper(Error));
function undefinedIfEmpty(array) {
  return array === void 0 || array.length === 0 ? void 0 : array;
}
function printError(error) {
  var output = error.message;
  if (error.nodes) {
    for (var _i4 = 0, _error$nodes2 = error.nodes; _i4 < _error$nodes2.length; _i4++) {
      var node = _error$nodes2[_i4];
      if (node.loc) {
        output += "\n\n" + printLocation(node.loc);
      }
    }
  } else if (error.source && error.locations) {
    for (var _i6 = 0, _error$locations2 = error.locations; _i6 < _error$locations2.length; _i6++) {
      var location2 = _error$locations2[_i6];
      output += "\n\n" + printSourceLocation(error.source, location2);
    }
  }
  return output;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/error/syntaxError.mjs
function syntaxError(source, position, description) {
  return new GraphQLError("Syntax Error: ".concat(description), void 0, source, [position]);
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/kinds.mjs
var Kind = Object.freeze({
  // Name
  NAME: "Name",
  // Document
  DOCUMENT: "Document",
  OPERATION_DEFINITION: "OperationDefinition",
  VARIABLE_DEFINITION: "VariableDefinition",
  SELECTION_SET: "SelectionSet",
  FIELD: "Field",
  ARGUMENT: "Argument",
  // Fragments
  FRAGMENT_SPREAD: "FragmentSpread",
  INLINE_FRAGMENT: "InlineFragment",
  FRAGMENT_DEFINITION: "FragmentDefinition",
  // Values
  VARIABLE: "Variable",
  INT: "IntValue",
  FLOAT: "FloatValue",
  STRING: "StringValue",
  BOOLEAN: "BooleanValue",
  NULL: "NullValue",
  ENUM: "EnumValue",
  LIST: "ListValue",
  OBJECT: "ObjectValue",
  OBJECT_FIELD: "ObjectField",
  // Directives
  DIRECTIVE: "Directive",
  // Types
  NAMED_TYPE: "NamedType",
  LIST_TYPE: "ListType",
  NON_NULL_TYPE: "NonNullType",
  // Type System Definitions
  SCHEMA_DEFINITION: "SchemaDefinition",
  OPERATION_TYPE_DEFINITION: "OperationTypeDefinition",
  // Type Definitions
  SCALAR_TYPE_DEFINITION: "ScalarTypeDefinition",
  OBJECT_TYPE_DEFINITION: "ObjectTypeDefinition",
  FIELD_DEFINITION: "FieldDefinition",
  INPUT_VALUE_DEFINITION: "InputValueDefinition",
  INTERFACE_TYPE_DEFINITION: "InterfaceTypeDefinition",
  UNION_TYPE_DEFINITION: "UnionTypeDefinition",
  ENUM_TYPE_DEFINITION: "EnumTypeDefinition",
  ENUM_VALUE_DEFINITION: "EnumValueDefinition",
  INPUT_OBJECT_TYPE_DEFINITION: "InputObjectTypeDefinition",
  // Directive Definitions
  DIRECTIVE_DEFINITION: "DirectiveDefinition",
  // Type System Extensions
  SCHEMA_EXTENSION: "SchemaExtension",
  // Type Extensions
  SCALAR_TYPE_EXTENSION: "ScalarTypeExtension",
  OBJECT_TYPE_EXTENSION: "ObjectTypeExtension",
  INTERFACE_TYPE_EXTENSION: "InterfaceTypeExtension",
  UNION_TYPE_EXTENSION: "UnionTypeExtension",
  ENUM_TYPE_EXTENSION: "EnumTypeExtension",
  INPUT_OBJECT_TYPE_EXTENSION: "InputObjectTypeExtension"
});

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/invariant.mjs
function invariant(condition, message) {
  var booleanCondition = Boolean(condition);
  if (!booleanCondition) {
    throw new Error(message != null ? message : "Unexpected invariant triggered.");
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/nodejsCustomInspectSymbol.mjs
var nodejsCustomInspectSymbol = typeof Symbol === "function" && typeof Symbol.for === "function" ? Symbol.for("nodejs.util.inspect.custom") : void 0;
var nodejsCustomInspectSymbol_default = nodejsCustomInspectSymbol;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/defineInspect.mjs
function defineInspect(classObject) {
  var fn = classObject.prototype.toJSON;
  typeof fn === "function" || invariant(0);
  classObject.prototype.inspect = fn;
  if (nodejsCustomInspectSymbol_default) {
    classObject.prototype[nodejsCustomInspectSymbol_default] = fn;
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/ast.mjs
var Location = function() {
  function Location2(startToken, endToken, source) {
    this.start = startToken.start;
    this.end = endToken.end;
    this.startToken = startToken;
    this.endToken = endToken;
    this.source = source;
  }
  var _proto = Location2.prototype;
  _proto.toJSON = function toJSON3() {
    return {
      start: this.start,
      end: this.end
    };
  };
  return Location2;
}();
defineInspect(Location);
var Token = function() {
  function Token2(kind, start, end, line, column, prev, value) {
    this.kind = kind;
    this.start = start;
    this.end = end;
    this.line = line;
    this.column = column;
    this.value = value;
    this.prev = prev;
    this.next = null;
  }
  var _proto2 = Token2.prototype;
  _proto2.toJSON = function toJSON3() {
    return {
      kind: this.kind,
      value: this.value,
      line: this.line,
      column: this.column
    };
  };
  return Token2;
}();
defineInspect(Token);
function isNode(maybeNode) {
  return maybeNode != null && typeof maybeNode.kind === "string";
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/tokenKind.mjs
var TokenKind = Object.freeze({
  SOF: "<SOF>",
  EOF: "<EOF>",
  BANG: "!",
  DOLLAR: "$",
  AMP: "&",
  PAREN_L: "(",
  PAREN_R: ")",
  SPREAD: "...",
  COLON: ":",
  EQUALS: "=",
  AT: "@",
  BRACKET_L: "[",
  BRACKET_R: "]",
  BRACE_L: "{",
  PIPE: "|",
  BRACE_R: "}",
  NAME: "Name",
  INT: "Int",
  FLOAT: "Float",
  STRING: "String",
  BLOCK_STRING: "BlockString",
  COMMENT: "Comment"
});

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/inspect.mjs
function _typeof3(obj) {
  "@babel/helpers - typeof";
  if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") {
    _typeof3 = function _typeof6(obj2) {
      return typeof obj2;
    };
  } else {
    _typeof3 = function _typeof6(obj2) {
      return obj2 && typeof Symbol === "function" && obj2.constructor === Symbol && obj2 !== Symbol.prototype ? "symbol" : typeof obj2;
    };
  }
  return _typeof3(obj);
}
var MAX_ARRAY_LENGTH = 10;
var MAX_RECURSIVE_DEPTH = 2;
function inspect(value) {
  return formatValue(value, []);
}
function formatValue(value, seenValues) {
  switch (_typeof3(value)) {
    case "string":
      return JSON.stringify(value);
    case "function":
      return value.name ? "[function ".concat(value.name, "]") : "[function]";
    case "object":
      if (value === null) {
        return "null";
      }
      return formatObjectValue(value, seenValues);
    default:
      return String(value);
  }
}
function formatObjectValue(value, previouslySeenValues) {
  if (previouslySeenValues.indexOf(value) !== -1) {
    return "[Circular]";
  }
  var seenValues = [].concat(previouslySeenValues, [value]);
  var customInspectFn = getCustomFn(value);
  if (customInspectFn !== void 0) {
    var customValue = customInspectFn.call(value);
    if (customValue !== value) {
      return typeof customValue === "string" ? customValue : formatValue(customValue, seenValues);
    }
  } else if (Array.isArray(value)) {
    return formatArray(value, seenValues);
  }
  return formatObject(value, seenValues);
}
function formatObject(object, seenValues) {
  var keys = Object.keys(object);
  if (keys.length === 0) {
    return "{}";
  }
  if (seenValues.length > MAX_RECURSIVE_DEPTH) {
    return "[" + getObjectTag(object) + "]";
  }
  var properties = keys.map(function(key) {
    var value = formatValue(object[key], seenValues);
    return key + ": " + value;
  });
  return "{ " + properties.join(", ") + " }";
}
function formatArray(array, seenValues) {
  if (array.length === 0) {
    return "[]";
  }
  if (seenValues.length > MAX_RECURSIVE_DEPTH) {
    return "[Array]";
  }
  var len = Math.min(MAX_ARRAY_LENGTH, array.length);
  var remaining = array.length - len;
  var items = [];
  for (var i = 0; i < len; ++i) {
    items.push(formatValue(array[i], seenValues));
  }
  if (remaining === 1) {
    items.push("... 1 more item");
  } else if (remaining > 1) {
    items.push("... ".concat(remaining, " more items"));
  }
  return "[" + items.join(", ") + "]";
}
function getCustomFn(object) {
  var customInspectFn = object[String(nodejsCustomInspectSymbol_default)];
  if (typeof customInspectFn === "function") {
    return customInspectFn;
  }
  if (typeof object.inspect === "function") {
    return object.inspect;
  }
}
function getObjectTag(object) {
  var tag = Object.prototype.toString.call(object).replace(/^\[object /, "").replace(/]$/, "");
  if (tag === "Object" && typeof object.constructor === "function") {
    var name = object.constructor.name;
    if (typeof name === "string" && name !== "") {
      return name;
    }
  }
  return tag;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/devAssert.mjs
function devAssert(condition, message) {
  var booleanCondition = Boolean(condition);
  if (!booleanCondition) {
    throw new Error(message);
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/instanceOf.mjs
function _typeof4(obj) {
  "@babel/helpers - typeof";
  if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") {
    _typeof4 = function _typeof6(obj2) {
      return typeof obj2;
    };
  } else {
    _typeof4 = function _typeof6(obj2) {
      return obj2 && typeof Symbol === "function" && obj2.constructor === Symbol && obj2 !== Symbol.prototype ? "symbol" : typeof obj2;
    };
  }
  return _typeof4(obj);
}
var instanceOf_default = false ? (
  // istanbul ignore next (See: 'https://github.com/graphql/graphql-js/issues/2317')
  // eslint-disable-next-line no-shadow
  function instanceOf(value, constructor) {
    return value instanceof constructor;
  }
) : (
  // eslint-disable-next-line no-shadow
  function instanceOf2(value, constructor) {
    if (value instanceof constructor) {
      return true;
    }
    if (_typeof4(value) === "object" && value !== null) {
      var _value$constructor;
      var className = constructor.prototype[Symbol.toStringTag];
      var valueClassName = (
        // We still need to support constructor's name to detect conflicts with older versions of this library.
        Symbol.toStringTag in value ? value[Symbol.toStringTag] : (_value$constructor = value.constructor) === null || _value$constructor === void 0 ? void 0 : _value$constructor.name
      );
      if (className === valueClassName) {
        var stringifiedValue = inspect(value);
        throw new Error("Cannot use ".concat(className, ' "').concat(stringifiedValue, '" from another module or realm.\n\nEnsure that there is only one instance of "graphql" in the node_modules\ndirectory. If different versions of "graphql" are the dependencies of other\nrelied on modules, use "resolutions" to ensure only one version is installed.\n\nhttps://yarnpkg.com/en/docs/selective-version-resolutions\n\nDuplicate "graphql" modules cannot be used at the same time since different\nversions may have different capabilities and behavior. The data from one\nversion used in the function from another could produce confusing and\nspurious results.'));
      }
    }
    return false;
  }
);

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/source.mjs
function _defineProperties2(target, props) {
  for (var i = 0; i < props.length; i++) {
    var descriptor = props[i];
    descriptor.enumerable = descriptor.enumerable || false;
    descriptor.configurable = true;
    if ("value" in descriptor) descriptor.writable = true;
    Object.defineProperty(target, descriptor.key, descriptor);
  }
}
function _createClass2(Constructor, protoProps, staticProps) {
  if (protoProps) _defineProperties2(Constructor.prototype, protoProps);
  if (staticProps) _defineProperties2(Constructor, staticProps);
  return Constructor;
}
var Source = function() {
  function Source2(body) {
    var name = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : "GraphQL request";
    var locationOffset = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : {
      line: 1,
      column: 1
    };
    typeof body === "string" || devAssert(0, "Body must be a string. Received: ".concat(inspect(body), "."));
    this.body = body;
    this.name = name;
    this.locationOffset = locationOffset;
    this.locationOffset.line > 0 || devAssert(0, "line in locationOffset is 1-indexed and must be positive.");
    this.locationOffset.column > 0 || devAssert(0, "column in locationOffset is 1-indexed and must be positive.");
  }
  _createClass2(Source2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "Source";
    }
  }]);
  return Source2;
}();
function isSource(source) {
  return instanceOf_default(source, Source);
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/directiveLocation.mjs
var DirectiveLocation = Object.freeze({
  // Request Definitions
  QUERY: "QUERY",
  MUTATION: "MUTATION",
  SUBSCRIPTION: "SUBSCRIPTION",
  FIELD: "FIELD",
  FRAGMENT_DEFINITION: "FRAGMENT_DEFINITION",
  FRAGMENT_SPREAD: "FRAGMENT_SPREAD",
  INLINE_FRAGMENT: "INLINE_FRAGMENT",
  VARIABLE_DEFINITION: "VARIABLE_DEFINITION",
  // Type System Definitions
  SCHEMA: "SCHEMA",
  SCALAR: "SCALAR",
  OBJECT: "OBJECT",
  FIELD_DEFINITION: "FIELD_DEFINITION",
  ARGUMENT_DEFINITION: "ARGUMENT_DEFINITION",
  INTERFACE: "INTERFACE",
  UNION: "UNION",
  ENUM: "ENUM",
  ENUM_VALUE: "ENUM_VALUE",
  INPUT_OBJECT: "INPUT_OBJECT",
  INPUT_FIELD_DEFINITION: "INPUT_FIELD_DEFINITION"
});

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/blockString.mjs
function dedentBlockStringValue(rawString) {
  var lines = rawString.split(/\r\n|[\n\r]/g);
  var commonIndent = getBlockStringIndentation(rawString);
  if (commonIndent !== 0) {
    for (var i = 1; i < lines.length; i++) {
      lines[i] = lines[i].slice(commonIndent);
    }
  }
  var startLine = 0;
  while (startLine < lines.length && isBlank(lines[startLine])) {
    ++startLine;
  }
  var endLine = lines.length;
  while (endLine > startLine && isBlank(lines[endLine - 1])) {
    --endLine;
  }
  return lines.slice(startLine, endLine).join("\n");
}
function isBlank(str) {
  for (var i = 0; i < str.length; ++i) {
    if (str[i] !== " " && str[i] !== "	") {
      return false;
    }
  }
  return true;
}
function getBlockStringIndentation(value) {
  var _commonIndent;
  var isFirstLine = true;
  var isEmptyLine = true;
  var indent2 = 0;
  var commonIndent = null;
  for (var i = 0; i < value.length; ++i) {
    switch (value.charCodeAt(i)) {
      case 13:
        if (value.charCodeAt(i + 1) === 10) {
          ++i;
        }
      case 10:
        isFirstLine = false;
        isEmptyLine = true;
        indent2 = 0;
        break;
      case 9:
      case 32:
        ++indent2;
        break;
      default:
        if (isEmptyLine && !isFirstLine && (commonIndent === null || indent2 < commonIndent)) {
          commonIndent = indent2;
        }
        isEmptyLine = false;
    }
  }
  return (_commonIndent = commonIndent) !== null && _commonIndent !== void 0 ? _commonIndent : 0;
}
function printBlockString(value) {
  var indentation = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : "";
  var preferMultipleLines = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : false;
  var isSingleLine = value.indexOf("\n") === -1;
  var hasLeadingSpace = value[0] === " " || value[0] === "	";
  var hasTrailingQuote = value[value.length - 1] === '"';
  var hasTrailingSlash = value[value.length - 1] === "\\";
  var printAsMultipleLines = !isSingleLine || hasTrailingQuote || hasTrailingSlash || preferMultipleLines;
  var result = "";
  if (printAsMultipleLines && !(isSingleLine && hasLeadingSpace)) {
    result += "\n" + indentation;
  }
  result += indentation ? value.replace(/\n/g, "\n" + indentation) : value;
  if (printAsMultipleLines) {
    result += "\n";
  }
  return '"""' + result.replace(/"""/g, '\\"""') + '"""';
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/lexer.mjs
var Lexer = function() {
  function Lexer2(source) {
    var startOfFileToken = new Token(TokenKind.SOF, 0, 0, 0, 0, null);
    this.source = source;
    this.lastToken = startOfFileToken;
    this.token = startOfFileToken;
    this.line = 1;
    this.lineStart = 0;
  }
  var _proto = Lexer2.prototype;
  _proto.advance = function advance() {
    this.lastToken = this.token;
    var token = this.token = this.lookahead();
    return token;
  };
  _proto.lookahead = function lookahead() {
    var token = this.token;
    if (token.kind !== TokenKind.EOF) {
      do {
        var _token$next;
        token = (_token$next = token.next) !== null && _token$next !== void 0 ? _token$next : token.next = readToken(this, token);
      } while (token.kind === TokenKind.COMMENT);
    }
    return token;
  };
  return Lexer2;
}();
function isPunctuatorTokenKind(kind) {
  return kind === TokenKind.BANG || kind === TokenKind.DOLLAR || kind === TokenKind.AMP || kind === TokenKind.PAREN_L || kind === TokenKind.PAREN_R || kind === TokenKind.SPREAD || kind === TokenKind.COLON || kind === TokenKind.EQUALS || kind === TokenKind.AT || kind === TokenKind.BRACKET_L || kind === TokenKind.BRACKET_R || kind === TokenKind.BRACE_L || kind === TokenKind.PIPE || kind === TokenKind.BRACE_R;
}
function printCharCode(code) {
  return (
    // NaN/undefined represents access beyond the end of the file.
    isNaN(code) ? TokenKind.EOF : (
      // Trust JSON for ASCII.
      code < 127 ? JSON.stringify(String.fromCharCode(code)) : (
        // Otherwise print the escaped form.
        '"\\u'.concat(("00" + code.toString(16).toUpperCase()).slice(-4), '"')
      )
    )
  );
}
function readToken(lexer, prev) {
  var source = lexer.source;
  var body = source.body;
  var bodyLength = body.length;
  var pos = prev.end;
  while (pos < bodyLength) {
    var code = body.charCodeAt(pos);
    var _line = lexer.line;
    var _col = 1 + pos - lexer.lineStart;
    switch (code) {
      case 65279:
      case 9:
      case 32:
      case 44:
        ++pos;
        continue;
      case 10:
        ++pos;
        ++lexer.line;
        lexer.lineStart = pos;
        continue;
      case 13:
        if (body.charCodeAt(pos + 1) === 10) {
          pos += 2;
        } else {
          ++pos;
        }
        ++lexer.line;
        lexer.lineStart = pos;
        continue;
      case 33:
        return new Token(TokenKind.BANG, pos, pos + 1, _line, _col, prev);
      case 35:
        return readComment(source, pos, _line, _col, prev);
      case 36:
        return new Token(TokenKind.DOLLAR, pos, pos + 1, _line, _col, prev);
      case 38:
        return new Token(TokenKind.AMP, pos, pos + 1, _line, _col, prev);
      case 40:
        return new Token(TokenKind.PAREN_L, pos, pos + 1, _line, _col, prev);
      case 41:
        return new Token(TokenKind.PAREN_R, pos, pos + 1, _line, _col, prev);
      case 46:
        if (body.charCodeAt(pos + 1) === 46 && body.charCodeAt(pos + 2) === 46) {
          return new Token(TokenKind.SPREAD, pos, pos + 3, _line, _col, prev);
        }
        break;
      case 58:
        return new Token(TokenKind.COLON, pos, pos + 1, _line, _col, prev);
      case 61:
        return new Token(TokenKind.EQUALS, pos, pos + 1, _line, _col, prev);
      case 64:
        return new Token(TokenKind.AT, pos, pos + 1, _line, _col, prev);
      case 91:
        return new Token(TokenKind.BRACKET_L, pos, pos + 1, _line, _col, prev);
      case 93:
        return new Token(TokenKind.BRACKET_R, pos, pos + 1, _line, _col, prev);
      case 123:
        return new Token(TokenKind.BRACE_L, pos, pos + 1, _line, _col, prev);
      case 124:
        return new Token(TokenKind.PIPE, pos, pos + 1, _line, _col, prev);
      case 125:
        return new Token(TokenKind.BRACE_R, pos, pos + 1, _line, _col, prev);
      case 34:
        if (body.charCodeAt(pos + 1) === 34 && body.charCodeAt(pos + 2) === 34) {
          return readBlockString(source, pos, _line, _col, prev, lexer);
        }
        return readString(source, pos, _line, _col, prev);
      case 45:
      case 48:
      case 49:
      case 50:
      case 51:
      case 52:
      case 53:
      case 54:
      case 55:
      case 56:
      case 57:
        return readNumber(source, pos, code, _line, _col, prev);
      case 65:
      case 66:
      case 67:
      case 68:
      case 69:
      case 70:
      case 71:
      case 72:
      case 73:
      case 74:
      case 75:
      case 76:
      case 77:
      case 78:
      case 79:
      case 80:
      case 81:
      case 82:
      case 83:
      case 84:
      case 85:
      case 86:
      case 87:
      case 88:
      case 89:
      case 90:
      case 95:
      case 97:
      case 98:
      case 99:
      case 100:
      case 101:
      case 102:
      case 103:
      case 104:
      case 105:
      case 106:
      case 107:
      case 108:
      case 109:
      case 110:
      case 111:
      case 112:
      case 113:
      case 114:
      case 115:
      case 116:
      case 117:
      case 118:
      case 119:
      case 120:
      case 121:
      case 122:
        return readName(source, pos, _line, _col, prev);
    }
    throw syntaxError(source, pos, unexpectedCharacterMessage(code));
  }
  var line = lexer.line;
  var col = 1 + pos - lexer.lineStart;
  return new Token(TokenKind.EOF, bodyLength, bodyLength, line, col, prev);
}
function unexpectedCharacterMessage(code) {
  if (code < 32 && code !== 9 && code !== 10 && code !== 13) {
    return "Cannot contain the invalid character ".concat(printCharCode(code), ".");
  }
  if (code === 39) {
    return `Unexpected single quote character ('), did you mean to use a double quote (")?`;
  }
  return "Cannot parse the unexpected character ".concat(printCharCode(code), ".");
}
function readComment(source, start, line, col, prev) {
  var body = source.body;
  var code;
  var position = start;
  do {
    code = body.charCodeAt(++position);
  } while (!isNaN(code) && // SourceCharacter but not LineTerminator
  (code > 31 || code === 9));
  return new Token(TokenKind.COMMENT, start, position, line, col, prev, body.slice(start + 1, position));
}
function readNumber(source, start, firstCode, line, col, prev) {
  var body = source.body;
  var code = firstCode;
  var position = start;
  var isFloat = false;
  if (code === 45) {
    code = body.charCodeAt(++position);
  }
  if (code === 48) {
    code = body.charCodeAt(++position);
    if (code >= 48 && code <= 57) {
      throw syntaxError(source, position, "Invalid number, unexpected digit after 0: ".concat(printCharCode(code), "."));
    }
  } else {
    position = readDigits(source, position, code);
    code = body.charCodeAt(position);
  }
  if (code === 46) {
    isFloat = true;
    code = body.charCodeAt(++position);
    position = readDigits(source, position, code);
    code = body.charCodeAt(position);
  }
  if (code === 69 || code === 101) {
    isFloat = true;
    code = body.charCodeAt(++position);
    if (code === 43 || code === 45) {
      code = body.charCodeAt(++position);
    }
    position = readDigits(source, position, code);
    code = body.charCodeAt(position);
  }
  if (code === 46 || isNameStart(code)) {
    throw syntaxError(source, position, "Invalid number, expected digit but got: ".concat(printCharCode(code), "."));
  }
  return new Token(isFloat ? TokenKind.FLOAT : TokenKind.INT, start, position, line, col, prev, body.slice(start, position));
}
function readDigits(source, start, firstCode) {
  var body = source.body;
  var position = start;
  var code = firstCode;
  if (code >= 48 && code <= 57) {
    do {
      code = body.charCodeAt(++position);
    } while (code >= 48 && code <= 57);
    return position;
  }
  throw syntaxError(source, position, "Invalid number, expected digit but got: ".concat(printCharCode(code), "."));
}
function readString(source, start, line, col, prev) {
  var body = source.body;
  var position = start + 1;
  var chunkStart = position;
  var code = 0;
  var value = "";
  while (position < body.length && !isNaN(code = body.charCodeAt(position)) && // not LineTerminator
  code !== 10 && code !== 13) {
    if (code === 34) {
      value += body.slice(chunkStart, position);
      return new Token(TokenKind.STRING, start, position + 1, line, col, prev, value);
    }
    if (code < 32 && code !== 9) {
      throw syntaxError(source, position, "Invalid character within String: ".concat(printCharCode(code), "."));
    }
    ++position;
    if (code === 92) {
      value += body.slice(chunkStart, position - 1);
      code = body.charCodeAt(position);
      switch (code) {
        case 34:
          value += '"';
          break;
        case 47:
          value += "/";
          break;
        case 92:
          value += "\\";
          break;
        case 98:
          value += "\b";
          break;
        case 102:
          value += "\f";
          break;
        case 110:
          value += "\n";
          break;
        case 114:
          value += "\r";
          break;
        case 116:
          value += "	";
          break;
        case 117: {
          var charCode = uniCharCode(body.charCodeAt(position + 1), body.charCodeAt(position + 2), body.charCodeAt(position + 3), body.charCodeAt(position + 4));
          if (charCode < 0) {
            var invalidSequence = body.slice(position + 1, position + 5);
            throw syntaxError(source, position, "Invalid character escape sequence: \\u".concat(invalidSequence, "."));
          }
          value += String.fromCharCode(charCode);
          position += 4;
          break;
        }
        default:
          throw syntaxError(source, position, "Invalid character escape sequence: \\".concat(String.fromCharCode(code), "."));
      }
      ++position;
      chunkStart = position;
    }
  }
  throw syntaxError(source, position, "Unterminated string.");
}
function readBlockString(source, start, line, col, prev, lexer) {
  var body = source.body;
  var position = start + 3;
  var chunkStart = position;
  var code = 0;
  var rawValue = "";
  while (position < body.length && !isNaN(code = body.charCodeAt(position))) {
    if (code === 34 && body.charCodeAt(position + 1) === 34 && body.charCodeAt(position + 2) === 34) {
      rawValue += body.slice(chunkStart, position);
      return new Token(TokenKind.BLOCK_STRING, start, position + 3, line, col, prev, dedentBlockStringValue(rawValue));
    }
    if (code < 32 && code !== 9 && code !== 10 && code !== 13) {
      throw syntaxError(source, position, "Invalid character within String: ".concat(printCharCode(code), "."));
    }
    if (code === 10) {
      ++position;
      ++lexer.line;
      lexer.lineStart = position;
    } else if (code === 13) {
      if (body.charCodeAt(position + 1) === 10) {
        position += 2;
      } else {
        ++position;
      }
      ++lexer.line;
      lexer.lineStart = position;
    } else if (
      // Escape Triple-Quote (\""")
      code === 92 && body.charCodeAt(position + 1) === 34 && body.charCodeAt(position + 2) === 34 && body.charCodeAt(position + 3) === 34
    ) {
      rawValue += body.slice(chunkStart, position) + '"""';
      position += 4;
      chunkStart = position;
    } else {
      ++position;
    }
  }
  throw syntaxError(source, position, "Unterminated string.");
}
function uniCharCode(a, b, c, d) {
  return char2hex(a) << 12 | char2hex(b) << 8 | char2hex(c) << 4 | char2hex(d);
}
function char2hex(a) {
  return a >= 48 && a <= 57 ? a - 48 : a >= 65 && a <= 70 ? a - 55 : a >= 97 && a <= 102 ? a - 87 : -1;
}
function readName(source, start, line, col, prev) {
  var body = source.body;
  var bodyLength = body.length;
  var position = start + 1;
  var code = 0;
  while (position !== bodyLength && !isNaN(code = body.charCodeAt(position)) && (code === 95 || // _
  code >= 48 && code <= 57 || // 0-9
  code >= 65 && code <= 90 || // A-Z
  code >= 97 && code <= 122)) {
    ++position;
  }
  return new Token(TokenKind.NAME, start, position, line, col, prev, body.slice(start, position));
}
function isNameStart(code) {
  return code === 95 || code >= 65 && code <= 90 || code >= 97 && code <= 122;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/parser.mjs
function parse(source, options) {
  var parser = new Parser(source, options);
  return parser.parseDocument();
}
var Parser = function() {
  function Parser2(source, options) {
    var sourceObj = isSource(source) ? source : new Source(source);
    this._lexer = new Lexer(sourceObj);
    this._options = options;
  }
  var _proto = Parser2.prototype;
  _proto.parseName = function parseName() {
    var token = this.expectToken(TokenKind.NAME);
    return {
      kind: Kind.NAME,
      value: token.value,
      loc: this.loc(token)
    };
  };
  _proto.parseDocument = function parseDocument() {
    var start = this._lexer.token;
    return {
      kind: Kind.DOCUMENT,
      definitions: this.many(TokenKind.SOF, this.parseDefinition, TokenKind.EOF),
      loc: this.loc(start)
    };
  };
  _proto.parseDefinition = function parseDefinition() {
    if (this.peek(TokenKind.NAME)) {
      switch (this._lexer.token.value) {
        case "query":
        case "mutation":
        case "subscription":
          return this.parseOperationDefinition();
        case "fragment":
          return this.parseFragmentDefinition();
        case "schema":
        case "scalar":
        case "type":
        case "interface":
        case "union":
        case "enum":
        case "input":
        case "directive":
          return this.parseTypeSystemDefinition();
        case "extend":
          return this.parseTypeSystemExtension();
      }
    } else if (this.peek(TokenKind.BRACE_L)) {
      return this.parseOperationDefinition();
    } else if (this.peekDescription()) {
      return this.parseTypeSystemDefinition();
    }
    throw this.unexpected();
  };
  _proto.parseOperationDefinition = function parseOperationDefinition() {
    var start = this._lexer.token;
    if (this.peek(TokenKind.BRACE_L)) {
      return {
        kind: Kind.OPERATION_DEFINITION,
        operation: "query",
        name: void 0,
        variableDefinitions: [],
        directives: [],
        selectionSet: this.parseSelectionSet(),
        loc: this.loc(start)
      };
    }
    var operation = this.parseOperationType();
    var name;
    if (this.peek(TokenKind.NAME)) {
      name = this.parseName();
    }
    return {
      kind: Kind.OPERATION_DEFINITION,
      operation,
      name,
      variableDefinitions: this.parseVariableDefinitions(),
      directives: this.parseDirectives(false),
      selectionSet: this.parseSelectionSet(),
      loc: this.loc(start)
    };
  };
  _proto.parseOperationType = function parseOperationType() {
    var operationToken = this.expectToken(TokenKind.NAME);
    switch (operationToken.value) {
      case "query":
        return "query";
      case "mutation":
        return "mutation";
      case "subscription":
        return "subscription";
    }
    throw this.unexpected(operationToken);
  };
  _proto.parseVariableDefinitions = function parseVariableDefinitions() {
    return this.optionalMany(TokenKind.PAREN_L, this.parseVariableDefinition, TokenKind.PAREN_R);
  };
  _proto.parseVariableDefinition = function parseVariableDefinition() {
    var start = this._lexer.token;
    return {
      kind: Kind.VARIABLE_DEFINITION,
      variable: this.parseVariable(),
      type: (this.expectToken(TokenKind.COLON), this.parseTypeReference()),
      defaultValue: this.expectOptionalToken(TokenKind.EQUALS) ? this.parseValueLiteral(true) : void 0,
      directives: this.parseDirectives(true),
      loc: this.loc(start)
    };
  };
  _proto.parseVariable = function parseVariable() {
    var start = this._lexer.token;
    this.expectToken(TokenKind.DOLLAR);
    return {
      kind: Kind.VARIABLE,
      name: this.parseName(),
      loc: this.loc(start)
    };
  };
  _proto.parseSelectionSet = function parseSelectionSet() {
    var start = this._lexer.token;
    return {
      kind: Kind.SELECTION_SET,
      selections: this.many(TokenKind.BRACE_L, this.parseSelection, TokenKind.BRACE_R),
      loc: this.loc(start)
    };
  };
  _proto.parseSelection = function parseSelection() {
    return this.peek(TokenKind.SPREAD) ? this.parseFragment() : this.parseField();
  };
  _proto.parseField = function parseField() {
    var start = this._lexer.token;
    var nameOrAlias = this.parseName();
    var alias;
    var name;
    if (this.expectOptionalToken(TokenKind.COLON)) {
      alias = nameOrAlias;
      name = this.parseName();
    } else {
      name = nameOrAlias;
    }
    return {
      kind: Kind.FIELD,
      alias,
      name,
      arguments: this.parseArguments(false),
      directives: this.parseDirectives(false),
      selectionSet: this.peek(TokenKind.BRACE_L) ? this.parseSelectionSet() : void 0,
      loc: this.loc(start)
    };
  };
  _proto.parseArguments = function parseArguments(isConst) {
    var item = isConst ? this.parseConstArgument : this.parseArgument;
    return this.optionalMany(TokenKind.PAREN_L, item, TokenKind.PAREN_R);
  };
  _proto.parseArgument = function parseArgument() {
    var start = this._lexer.token;
    var name = this.parseName();
    this.expectToken(TokenKind.COLON);
    return {
      kind: Kind.ARGUMENT,
      name,
      value: this.parseValueLiteral(false),
      loc: this.loc(start)
    };
  };
  _proto.parseConstArgument = function parseConstArgument() {
    var start = this._lexer.token;
    return {
      kind: Kind.ARGUMENT,
      name: this.parseName(),
      value: (this.expectToken(TokenKind.COLON), this.parseValueLiteral(true)),
      loc: this.loc(start)
    };
  };
  _proto.parseFragment = function parseFragment() {
    var start = this._lexer.token;
    this.expectToken(TokenKind.SPREAD);
    var hasTypeCondition = this.expectOptionalKeyword("on");
    if (!hasTypeCondition && this.peek(TokenKind.NAME)) {
      return {
        kind: Kind.FRAGMENT_SPREAD,
        name: this.parseFragmentName(),
        directives: this.parseDirectives(false),
        loc: this.loc(start)
      };
    }
    return {
      kind: Kind.INLINE_FRAGMENT,
      typeCondition: hasTypeCondition ? this.parseNamedType() : void 0,
      directives: this.parseDirectives(false),
      selectionSet: this.parseSelectionSet(),
      loc: this.loc(start)
    };
  };
  _proto.parseFragmentDefinition = function parseFragmentDefinition() {
    var _this$_options;
    var start = this._lexer.token;
    this.expectKeyword("fragment");
    if (((_this$_options = this._options) === null || _this$_options === void 0 ? void 0 : _this$_options.experimentalFragmentVariables) === true) {
      return {
        kind: Kind.FRAGMENT_DEFINITION,
        name: this.parseFragmentName(),
        variableDefinitions: this.parseVariableDefinitions(),
        typeCondition: (this.expectKeyword("on"), this.parseNamedType()),
        directives: this.parseDirectives(false),
        selectionSet: this.parseSelectionSet(),
        loc: this.loc(start)
      };
    }
    return {
      kind: Kind.FRAGMENT_DEFINITION,
      name: this.parseFragmentName(),
      typeCondition: (this.expectKeyword("on"), this.parseNamedType()),
      directives: this.parseDirectives(false),
      selectionSet: this.parseSelectionSet(),
      loc: this.loc(start)
    };
  };
  _proto.parseFragmentName = function parseFragmentName() {
    if (this._lexer.token.value === "on") {
      throw this.unexpected();
    }
    return this.parseName();
  };
  _proto.parseValueLiteral = function parseValueLiteral(isConst) {
    var token = this._lexer.token;
    switch (token.kind) {
      case TokenKind.BRACKET_L:
        return this.parseList(isConst);
      case TokenKind.BRACE_L:
        return this.parseObject(isConst);
      case TokenKind.INT:
        this._lexer.advance();
        return {
          kind: Kind.INT,
          value: token.value,
          loc: this.loc(token)
        };
      case TokenKind.FLOAT:
        this._lexer.advance();
        return {
          kind: Kind.FLOAT,
          value: token.value,
          loc: this.loc(token)
        };
      case TokenKind.STRING:
      case TokenKind.BLOCK_STRING:
        return this.parseStringLiteral();
      case TokenKind.NAME:
        this._lexer.advance();
        switch (token.value) {
          case "true":
            return {
              kind: Kind.BOOLEAN,
              value: true,
              loc: this.loc(token)
            };
          case "false":
            return {
              kind: Kind.BOOLEAN,
              value: false,
              loc: this.loc(token)
            };
          case "null":
            return {
              kind: Kind.NULL,
              loc: this.loc(token)
            };
          default:
            return {
              kind: Kind.ENUM,
              value: token.value,
              loc: this.loc(token)
            };
        }
      case TokenKind.DOLLAR:
        if (!isConst) {
          return this.parseVariable();
        }
        break;
    }
    throw this.unexpected();
  };
  _proto.parseStringLiteral = function parseStringLiteral() {
    var token = this._lexer.token;
    this._lexer.advance();
    return {
      kind: Kind.STRING,
      value: token.value,
      block: token.kind === TokenKind.BLOCK_STRING,
      loc: this.loc(token)
    };
  };
  _proto.parseList = function parseList(isConst) {
    var _this = this;
    var start = this._lexer.token;
    var item = function item2() {
      return _this.parseValueLiteral(isConst);
    };
    return {
      kind: Kind.LIST,
      values: this.any(TokenKind.BRACKET_L, item, TokenKind.BRACKET_R),
      loc: this.loc(start)
    };
  };
  _proto.parseObject = function parseObject(isConst) {
    var _this2 = this;
    var start = this._lexer.token;
    var item = function item2() {
      return _this2.parseObjectField(isConst);
    };
    return {
      kind: Kind.OBJECT,
      fields: this.any(TokenKind.BRACE_L, item, TokenKind.BRACE_R),
      loc: this.loc(start)
    };
  };
  _proto.parseObjectField = function parseObjectField(isConst) {
    var start = this._lexer.token;
    var name = this.parseName();
    this.expectToken(TokenKind.COLON);
    return {
      kind: Kind.OBJECT_FIELD,
      name,
      value: this.parseValueLiteral(isConst),
      loc: this.loc(start)
    };
  };
  _proto.parseDirectives = function parseDirectives(isConst) {
    var directives = [];
    while (this.peek(TokenKind.AT)) {
      directives.push(this.parseDirective(isConst));
    }
    return directives;
  };
  _proto.parseDirective = function parseDirective(isConst) {
    var start = this._lexer.token;
    this.expectToken(TokenKind.AT);
    return {
      kind: Kind.DIRECTIVE,
      name: this.parseName(),
      arguments: this.parseArguments(isConst),
      loc: this.loc(start)
    };
  };
  _proto.parseTypeReference = function parseTypeReference() {
    var start = this._lexer.token;
    var type;
    if (this.expectOptionalToken(TokenKind.BRACKET_L)) {
      type = this.parseTypeReference();
      this.expectToken(TokenKind.BRACKET_R);
      type = {
        kind: Kind.LIST_TYPE,
        type,
        loc: this.loc(start)
      };
    } else {
      type = this.parseNamedType();
    }
    if (this.expectOptionalToken(TokenKind.BANG)) {
      return {
        kind: Kind.NON_NULL_TYPE,
        type,
        loc: this.loc(start)
      };
    }
    return type;
  };
  _proto.parseNamedType = function parseNamedType() {
    var start = this._lexer.token;
    return {
      kind: Kind.NAMED_TYPE,
      name: this.parseName(),
      loc: this.loc(start)
    };
  };
  _proto.parseTypeSystemDefinition = function parseTypeSystemDefinition() {
    var keywordToken = this.peekDescription() ? this._lexer.lookahead() : this._lexer.token;
    if (keywordToken.kind === TokenKind.NAME) {
      switch (keywordToken.value) {
        case "schema":
          return this.parseSchemaDefinition();
        case "scalar":
          return this.parseScalarTypeDefinition();
        case "type":
          return this.parseObjectTypeDefinition();
        case "interface":
          return this.parseInterfaceTypeDefinition();
        case "union":
          return this.parseUnionTypeDefinition();
        case "enum":
          return this.parseEnumTypeDefinition();
        case "input":
          return this.parseInputObjectTypeDefinition();
        case "directive":
          return this.parseDirectiveDefinition();
      }
    }
    throw this.unexpected(keywordToken);
  };
  _proto.peekDescription = function peekDescription() {
    return this.peek(TokenKind.STRING) || this.peek(TokenKind.BLOCK_STRING);
  };
  _proto.parseDescription = function parseDescription() {
    if (this.peekDescription()) {
      return this.parseStringLiteral();
    }
  };
  _proto.parseSchemaDefinition = function parseSchemaDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("schema");
    var directives = this.parseDirectives(true);
    var operationTypes = this.many(TokenKind.BRACE_L, this.parseOperationTypeDefinition, TokenKind.BRACE_R);
    return {
      kind: Kind.SCHEMA_DEFINITION,
      description,
      directives,
      operationTypes,
      loc: this.loc(start)
    };
  };
  _proto.parseOperationTypeDefinition = function parseOperationTypeDefinition() {
    var start = this._lexer.token;
    var operation = this.parseOperationType();
    this.expectToken(TokenKind.COLON);
    var type = this.parseNamedType();
    return {
      kind: Kind.OPERATION_TYPE_DEFINITION,
      operation,
      type,
      loc: this.loc(start)
    };
  };
  _proto.parseScalarTypeDefinition = function parseScalarTypeDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("scalar");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    return {
      kind: Kind.SCALAR_TYPE_DEFINITION,
      description,
      name,
      directives,
      loc: this.loc(start)
    };
  };
  _proto.parseObjectTypeDefinition = function parseObjectTypeDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("type");
    var name = this.parseName();
    var interfaces = this.parseImplementsInterfaces();
    var directives = this.parseDirectives(true);
    var fields7 = this.parseFieldsDefinition();
    return {
      kind: Kind.OBJECT_TYPE_DEFINITION,
      description,
      name,
      interfaces,
      directives,
      fields: fields7,
      loc: this.loc(start)
    };
  };
  _proto.parseImplementsInterfaces = function parseImplementsInterfaces() {
    var _this$_options2;
    if (!this.expectOptionalKeyword("implements")) {
      return [];
    }
    if (((_this$_options2 = this._options) === null || _this$_options2 === void 0 ? void 0 : _this$_options2.allowLegacySDLImplementsInterfaces) === true) {
      var types = [];
      this.expectOptionalToken(TokenKind.AMP);
      do {
        types.push(this.parseNamedType());
      } while (this.expectOptionalToken(TokenKind.AMP) || this.peek(TokenKind.NAME));
      return types;
    }
    return this.delimitedMany(TokenKind.AMP, this.parseNamedType);
  };
  _proto.parseFieldsDefinition = function parseFieldsDefinition() {
    var _this$_options3;
    if (((_this$_options3 = this._options) === null || _this$_options3 === void 0 ? void 0 : _this$_options3.allowLegacySDLEmptyFields) === true && this.peek(TokenKind.BRACE_L) && this._lexer.lookahead().kind === TokenKind.BRACE_R) {
      this._lexer.advance();
      this._lexer.advance();
      return [];
    }
    return this.optionalMany(TokenKind.BRACE_L, this.parseFieldDefinition, TokenKind.BRACE_R);
  };
  _proto.parseFieldDefinition = function parseFieldDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    var name = this.parseName();
    var args = this.parseArgumentDefs();
    this.expectToken(TokenKind.COLON);
    var type = this.parseTypeReference();
    var directives = this.parseDirectives(true);
    return {
      kind: Kind.FIELD_DEFINITION,
      description,
      name,
      arguments: args,
      type,
      directives,
      loc: this.loc(start)
    };
  };
  _proto.parseArgumentDefs = function parseArgumentDefs() {
    return this.optionalMany(TokenKind.PAREN_L, this.parseInputValueDef, TokenKind.PAREN_R);
  };
  _proto.parseInputValueDef = function parseInputValueDef() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    var name = this.parseName();
    this.expectToken(TokenKind.COLON);
    var type = this.parseTypeReference();
    var defaultValue;
    if (this.expectOptionalToken(TokenKind.EQUALS)) {
      defaultValue = this.parseValueLiteral(true);
    }
    var directives = this.parseDirectives(true);
    return {
      kind: Kind.INPUT_VALUE_DEFINITION,
      description,
      name,
      type,
      defaultValue,
      directives,
      loc: this.loc(start)
    };
  };
  _proto.parseInterfaceTypeDefinition = function parseInterfaceTypeDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("interface");
    var name = this.parseName();
    var interfaces = this.parseImplementsInterfaces();
    var directives = this.parseDirectives(true);
    var fields7 = this.parseFieldsDefinition();
    return {
      kind: Kind.INTERFACE_TYPE_DEFINITION,
      description,
      name,
      interfaces,
      directives,
      fields: fields7,
      loc: this.loc(start)
    };
  };
  _proto.parseUnionTypeDefinition = function parseUnionTypeDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("union");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    var types = this.parseUnionMemberTypes();
    return {
      kind: Kind.UNION_TYPE_DEFINITION,
      description,
      name,
      directives,
      types,
      loc: this.loc(start)
    };
  };
  _proto.parseUnionMemberTypes = function parseUnionMemberTypes() {
    return this.expectOptionalToken(TokenKind.EQUALS) ? this.delimitedMany(TokenKind.PIPE, this.parseNamedType) : [];
  };
  _proto.parseEnumTypeDefinition = function parseEnumTypeDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("enum");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    var values = this.parseEnumValuesDefinition();
    return {
      kind: Kind.ENUM_TYPE_DEFINITION,
      description,
      name,
      directives,
      values,
      loc: this.loc(start)
    };
  };
  _proto.parseEnumValuesDefinition = function parseEnumValuesDefinition() {
    return this.optionalMany(TokenKind.BRACE_L, this.parseEnumValueDefinition, TokenKind.BRACE_R);
  };
  _proto.parseEnumValueDefinition = function parseEnumValueDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    return {
      kind: Kind.ENUM_VALUE_DEFINITION,
      description,
      name,
      directives,
      loc: this.loc(start)
    };
  };
  _proto.parseInputObjectTypeDefinition = function parseInputObjectTypeDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("input");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    var fields7 = this.parseInputFieldsDefinition();
    return {
      kind: Kind.INPUT_OBJECT_TYPE_DEFINITION,
      description,
      name,
      directives,
      fields: fields7,
      loc: this.loc(start)
    };
  };
  _proto.parseInputFieldsDefinition = function parseInputFieldsDefinition() {
    return this.optionalMany(TokenKind.BRACE_L, this.parseInputValueDef, TokenKind.BRACE_R);
  };
  _proto.parseTypeSystemExtension = function parseTypeSystemExtension() {
    var keywordToken = this._lexer.lookahead();
    if (keywordToken.kind === TokenKind.NAME) {
      switch (keywordToken.value) {
        case "schema":
          return this.parseSchemaExtension();
        case "scalar":
          return this.parseScalarTypeExtension();
        case "type":
          return this.parseObjectTypeExtension();
        case "interface":
          return this.parseInterfaceTypeExtension();
        case "union":
          return this.parseUnionTypeExtension();
        case "enum":
          return this.parseEnumTypeExtension();
        case "input":
          return this.parseInputObjectTypeExtension();
      }
    }
    throw this.unexpected(keywordToken);
  };
  _proto.parseSchemaExtension = function parseSchemaExtension() {
    var start = this._lexer.token;
    this.expectKeyword("extend");
    this.expectKeyword("schema");
    var directives = this.parseDirectives(true);
    var operationTypes = this.optionalMany(TokenKind.BRACE_L, this.parseOperationTypeDefinition, TokenKind.BRACE_R);
    if (directives.length === 0 && operationTypes.length === 0) {
      throw this.unexpected();
    }
    return {
      kind: Kind.SCHEMA_EXTENSION,
      directives,
      operationTypes,
      loc: this.loc(start)
    };
  };
  _proto.parseScalarTypeExtension = function parseScalarTypeExtension() {
    var start = this._lexer.token;
    this.expectKeyword("extend");
    this.expectKeyword("scalar");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    if (directives.length === 0) {
      throw this.unexpected();
    }
    return {
      kind: Kind.SCALAR_TYPE_EXTENSION,
      name,
      directives,
      loc: this.loc(start)
    };
  };
  _proto.parseObjectTypeExtension = function parseObjectTypeExtension() {
    var start = this._lexer.token;
    this.expectKeyword("extend");
    this.expectKeyword("type");
    var name = this.parseName();
    var interfaces = this.parseImplementsInterfaces();
    var directives = this.parseDirectives(true);
    var fields7 = this.parseFieldsDefinition();
    if (interfaces.length === 0 && directives.length === 0 && fields7.length === 0) {
      throw this.unexpected();
    }
    return {
      kind: Kind.OBJECT_TYPE_EXTENSION,
      name,
      interfaces,
      directives,
      fields: fields7,
      loc: this.loc(start)
    };
  };
  _proto.parseInterfaceTypeExtension = function parseInterfaceTypeExtension() {
    var start = this._lexer.token;
    this.expectKeyword("extend");
    this.expectKeyword("interface");
    var name = this.parseName();
    var interfaces = this.parseImplementsInterfaces();
    var directives = this.parseDirectives(true);
    var fields7 = this.parseFieldsDefinition();
    if (interfaces.length === 0 && directives.length === 0 && fields7.length === 0) {
      throw this.unexpected();
    }
    return {
      kind: Kind.INTERFACE_TYPE_EXTENSION,
      name,
      interfaces,
      directives,
      fields: fields7,
      loc: this.loc(start)
    };
  };
  _proto.parseUnionTypeExtension = function parseUnionTypeExtension() {
    var start = this._lexer.token;
    this.expectKeyword("extend");
    this.expectKeyword("union");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    var types = this.parseUnionMemberTypes();
    if (directives.length === 0 && types.length === 0) {
      throw this.unexpected();
    }
    return {
      kind: Kind.UNION_TYPE_EXTENSION,
      name,
      directives,
      types,
      loc: this.loc(start)
    };
  };
  _proto.parseEnumTypeExtension = function parseEnumTypeExtension() {
    var start = this._lexer.token;
    this.expectKeyword("extend");
    this.expectKeyword("enum");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    var values = this.parseEnumValuesDefinition();
    if (directives.length === 0 && values.length === 0) {
      throw this.unexpected();
    }
    return {
      kind: Kind.ENUM_TYPE_EXTENSION,
      name,
      directives,
      values,
      loc: this.loc(start)
    };
  };
  _proto.parseInputObjectTypeExtension = function parseInputObjectTypeExtension() {
    var start = this._lexer.token;
    this.expectKeyword("extend");
    this.expectKeyword("input");
    var name = this.parseName();
    var directives = this.parseDirectives(true);
    var fields7 = this.parseInputFieldsDefinition();
    if (directives.length === 0 && fields7.length === 0) {
      throw this.unexpected();
    }
    return {
      kind: Kind.INPUT_OBJECT_TYPE_EXTENSION,
      name,
      directives,
      fields: fields7,
      loc: this.loc(start)
    };
  };
  _proto.parseDirectiveDefinition = function parseDirectiveDefinition() {
    var start = this._lexer.token;
    var description = this.parseDescription();
    this.expectKeyword("directive");
    this.expectToken(TokenKind.AT);
    var name = this.parseName();
    var args = this.parseArgumentDefs();
    var repeatable = this.expectOptionalKeyword("repeatable");
    this.expectKeyword("on");
    var locations = this.parseDirectiveLocations();
    return {
      kind: Kind.DIRECTIVE_DEFINITION,
      description,
      name,
      arguments: args,
      repeatable,
      locations,
      loc: this.loc(start)
    };
  };
  _proto.parseDirectiveLocations = function parseDirectiveLocations() {
    return this.delimitedMany(TokenKind.PIPE, this.parseDirectiveLocation);
  };
  _proto.parseDirectiveLocation = function parseDirectiveLocation() {
    var start = this._lexer.token;
    var name = this.parseName();
    if (DirectiveLocation[name.value] !== void 0) {
      return name;
    }
    throw this.unexpected(start);
  };
  _proto.loc = function loc(startToken) {
    var _this$_options4;
    if (((_this$_options4 = this._options) === null || _this$_options4 === void 0 ? void 0 : _this$_options4.noLocation) !== true) {
      return new Location(startToken, this._lexer.lastToken, this._lexer.source);
    }
  };
  _proto.peek = function peek(kind) {
    return this._lexer.token.kind === kind;
  };
  _proto.expectToken = function expectToken(kind) {
    var token = this._lexer.token;
    if (token.kind === kind) {
      this._lexer.advance();
      return token;
    }
    throw syntaxError(this._lexer.source, token.start, "Expected ".concat(getTokenKindDesc(kind), ", found ").concat(getTokenDesc(token), "."));
  };
  _proto.expectOptionalToken = function expectOptionalToken(kind) {
    var token = this._lexer.token;
    if (token.kind === kind) {
      this._lexer.advance();
      return token;
    }
    return void 0;
  };
  _proto.expectKeyword = function expectKeyword(value) {
    var token = this._lexer.token;
    if (token.kind === TokenKind.NAME && token.value === value) {
      this._lexer.advance();
    } else {
      throw syntaxError(this._lexer.source, token.start, 'Expected "'.concat(value, '", found ').concat(getTokenDesc(token), "."));
    }
  };
  _proto.expectOptionalKeyword = function expectOptionalKeyword(value) {
    var token = this._lexer.token;
    if (token.kind === TokenKind.NAME && token.value === value) {
      this._lexer.advance();
      return true;
    }
    return false;
  };
  _proto.unexpected = function unexpected(atToken) {
    var token = atToken !== null && atToken !== void 0 ? atToken : this._lexer.token;
    return syntaxError(this._lexer.source, token.start, "Unexpected ".concat(getTokenDesc(token), "."));
  };
  _proto.any = function any(openKind, parseFn, closeKind) {
    this.expectToken(openKind);
    var nodes = [];
    while (!this.expectOptionalToken(closeKind)) {
      nodes.push(parseFn.call(this));
    }
    return nodes;
  };
  _proto.optionalMany = function optionalMany(openKind, parseFn, closeKind) {
    if (this.expectOptionalToken(openKind)) {
      var nodes = [];
      do {
        nodes.push(parseFn.call(this));
      } while (!this.expectOptionalToken(closeKind));
      return nodes;
    }
    return [];
  };
  _proto.many = function many(openKind, parseFn, closeKind) {
    this.expectToken(openKind);
    var nodes = [];
    do {
      nodes.push(parseFn.call(this));
    } while (!this.expectOptionalToken(closeKind));
    return nodes;
  };
  _proto.delimitedMany = function delimitedMany(delimiterKind, parseFn) {
    this.expectOptionalToken(delimiterKind);
    var nodes = [];
    do {
      nodes.push(parseFn.call(this));
    } while (this.expectOptionalToken(delimiterKind));
    return nodes;
  };
  return Parser2;
}();
function getTokenDesc(token) {
  var value = token.value;
  return getTokenKindDesc(token.kind) + (value != null ? ' "'.concat(value, '"') : "");
}
function getTokenKindDesc(kind) {
  return isPunctuatorTokenKind(kind) ? '"'.concat(kind, '"') : kind;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/visitor.mjs
var QueryDocumentKeys = {
  Name: [],
  Document: ["definitions"],
  OperationDefinition: ["name", "variableDefinitions", "directives", "selectionSet"],
  VariableDefinition: ["variable", "type", "defaultValue", "directives"],
  Variable: ["name"],
  SelectionSet: ["selections"],
  Field: ["alias", "name", "arguments", "directives", "selectionSet"],
  Argument: ["name", "value"],
  FragmentSpread: ["name", "directives"],
  InlineFragment: ["typeCondition", "directives", "selectionSet"],
  FragmentDefinition: [
    "name",
    // Note: fragment variable definitions are experimental and may be changed
    // or removed in the future.
    "variableDefinitions",
    "typeCondition",
    "directives",
    "selectionSet"
  ],
  IntValue: [],
  FloatValue: [],
  StringValue: [],
  BooleanValue: [],
  NullValue: [],
  EnumValue: [],
  ListValue: ["values"],
  ObjectValue: ["fields"],
  ObjectField: ["name", "value"],
  Directive: ["name", "arguments"],
  NamedType: ["name"],
  ListType: ["type"],
  NonNullType: ["type"],
  SchemaDefinition: ["description", "directives", "operationTypes"],
  OperationTypeDefinition: ["type"],
  ScalarTypeDefinition: ["description", "name", "directives"],
  ObjectTypeDefinition: ["description", "name", "interfaces", "directives", "fields"],
  FieldDefinition: ["description", "name", "arguments", "type", "directives"],
  InputValueDefinition: ["description", "name", "type", "defaultValue", "directives"],
  InterfaceTypeDefinition: ["description", "name", "interfaces", "directives", "fields"],
  UnionTypeDefinition: ["description", "name", "directives", "types"],
  EnumTypeDefinition: ["description", "name", "directives", "values"],
  EnumValueDefinition: ["description", "name", "directives"],
  InputObjectTypeDefinition: ["description", "name", "directives", "fields"],
  DirectiveDefinition: ["description", "name", "arguments", "locations"],
  SchemaExtension: ["directives", "operationTypes"],
  ScalarTypeExtension: ["name", "directives"],
  ObjectTypeExtension: ["name", "interfaces", "directives", "fields"],
  InterfaceTypeExtension: ["name", "interfaces", "directives", "fields"],
  UnionTypeExtension: ["name", "directives", "types"],
  EnumTypeExtension: ["name", "directives", "values"],
  InputObjectTypeExtension: ["name", "directives", "fields"]
};
var BREAK = Object.freeze({});
function visit(root, visitor) {
  var visitorKeys = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : QueryDocumentKeys;
  var stack = void 0;
  var inArray = Array.isArray(root);
  var keys = [root];
  var index = -1;
  var edits = [];
  var node = void 0;
  var key = void 0;
  var parent = void 0;
  var path = [];
  var ancestors = [];
  var newRoot = root;
  do {
    index++;
    var isLeaving = index === keys.length;
    var isEdited = isLeaving && edits.length !== 0;
    if (isLeaving) {
      key = ancestors.length === 0 ? void 0 : path[path.length - 1];
      node = parent;
      parent = ancestors.pop();
      if (isEdited) {
        if (inArray) {
          node = node.slice();
        } else {
          var clone = {};
          for (var _i2 = 0, _Object$keys2 = Object.keys(node); _i2 < _Object$keys2.length; _i2++) {
            var k = _Object$keys2[_i2];
            clone[k] = node[k];
          }
          node = clone;
        }
        var editOffset = 0;
        for (var ii = 0; ii < edits.length; ii++) {
          var editKey = edits[ii][0];
          var editValue = edits[ii][1];
          if (inArray) {
            editKey -= editOffset;
          }
          if (inArray && editValue === null) {
            node.splice(editKey, 1);
            editOffset++;
          } else {
            node[editKey] = editValue;
          }
        }
      }
      index = stack.index;
      keys = stack.keys;
      edits = stack.edits;
      inArray = stack.inArray;
      stack = stack.prev;
    } else {
      key = parent ? inArray ? index : keys[index] : void 0;
      node = parent ? parent[key] : newRoot;
      if (node === null || node === void 0) {
        continue;
      }
      if (parent) {
        path.push(key);
      }
    }
    var result = void 0;
    if (!Array.isArray(node)) {
      if (!isNode(node)) {
        throw new Error("Invalid AST Node: ".concat(inspect(node), "."));
      }
      var visitFn = getVisitFn(visitor, node.kind, isLeaving);
      if (visitFn) {
        result = visitFn.call(visitor, node, key, parent, path, ancestors);
        if (result === BREAK) {
          break;
        }
        if (result === false) {
          if (!isLeaving) {
            path.pop();
            continue;
          }
        } else if (result !== void 0) {
          edits.push([key, result]);
          if (!isLeaving) {
            if (isNode(result)) {
              node = result;
            } else {
              path.pop();
              continue;
            }
          }
        }
      }
    }
    if (result === void 0 && isEdited) {
      edits.push([key, node]);
    }
    if (isLeaving) {
      path.pop();
    } else {
      var _visitorKeys$node$kin;
      stack = {
        inArray,
        index,
        keys,
        edits,
        prev: stack
      };
      inArray = Array.isArray(node);
      keys = inArray ? node : (_visitorKeys$node$kin = visitorKeys[node.kind]) !== null && _visitorKeys$node$kin !== void 0 ? _visitorKeys$node$kin : [];
      index = -1;
      edits = [];
      if (parent) {
        ancestors.push(parent);
      }
      parent = node;
    }
  } while (stack !== void 0);
  if (edits.length !== 0) {
    newRoot = edits[edits.length - 1][1];
  }
  return newRoot;
}
function getVisitFn(visitor, kind, isLeaving) {
  var kindVisitor = visitor[kind];
  if (kindVisitor) {
    if (!isLeaving && typeof kindVisitor === "function") {
      return kindVisitor;
    }
    var kindSpecificVisitor = isLeaving ? kindVisitor.leave : kindVisitor.enter;
    if (typeof kindSpecificVisitor === "function") {
      return kindSpecificVisitor;
    }
  } else {
    var specificVisitor = isLeaving ? visitor.leave : visitor.enter;
    if (specificVisitor) {
      if (typeof specificVisitor === "function") {
        return specificVisitor;
      }
      var specificKindVisitor = specificVisitor[kind];
      if (typeof specificKindVisitor === "function") {
        return specificKindVisitor;
      }
    }
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/polyfills/find.mjs
var find = Array.prototype.find ? function(list, predicate) {
  return Array.prototype.find.call(list, predicate);
} : function(list, predicate) {
  for (var _i2 = 0; _i2 < list.length; _i2++) {
    var value = list[_i2];
    if (predicate(value)) {
      return value;
    }
  }
};
var find_default = find;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/polyfills/objectValues.mjs
var objectValues = Object.values || function(obj) {
  return Object.keys(obj).map(function(key) {
    return obj[key];
  });
};
var objectValues_default = objectValues;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/polyfills/objectEntries.mjs
var objectEntries = Object.entries || function(obj) {
  return Object.keys(obj).map(function(key) {
    return [key, obj[key]];
  });
};
var objectEntries_default = objectEntries;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/keyMap.mjs
function keyMap(list, keyFn) {
  return list.reduce(function(map2, item) {
    map2[keyFn(item)] = item;
    return map2;
  }, /* @__PURE__ */ Object.create(null));
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/mapValue.mjs
function mapValue(map2, fn) {
  var result = /* @__PURE__ */ Object.create(null);
  for (var _i2 = 0, _objectEntries2 = objectEntries_default(map2); _i2 < _objectEntries2.length; _i2++) {
    var _ref2 = _objectEntries2[_i2];
    var _key = _ref2[0];
    var _value = _ref2[1];
    result[_key] = fn(_value, _key);
  }
  return result;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/toObjMap.mjs
function toObjMap(obj) {
  if (Object.getPrototypeOf(obj) === null) {
    return obj;
  }
  var map2 = /* @__PURE__ */ Object.create(null);
  for (var _i2 = 0, _objectEntries2 = objectEntries_default(obj); _i2 < _objectEntries2.length; _i2++) {
    var _ref2 = _objectEntries2[_i2];
    var key = _ref2[0];
    var value = _ref2[1];
    map2[key] = value;
  }
  return map2;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/keyValMap.mjs
function keyValMap(list, keyFn, valFn) {
  return list.reduce(function(map2, item) {
    map2[keyFn(item)] = valFn(item);
    return map2;
  }, /* @__PURE__ */ Object.create(null));
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/didYouMean.mjs
var MAX_SUGGESTIONS = 5;
function didYouMean(firstArg, secondArg) {
  var _ref = typeof firstArg === "string" ? [firstArg, secondArg] : [void 0, firstArg], subMessage = _ref[0], suggestionsArg = _ref[1];
  var message = " Did you mean ";
  if (subMessage) {
    message += subMessage + " ";
  }
  var suggestions = suggestionsArg.map(function(x) {
    return '"'.concat(x, '"');
  });
  switch (suggestions.length) {
    case 0:
      return "";
    case 1:
      return message + suggestions[0] + "?";
    case 2:
      return message + suggestions[0] + " or " + suggestions[1] + "?";
  }
  var selected = suggestions.slice(0, MAX_SUGGESTIONS);
  var lastItem = selected.pop();
  return message + selected.join(", ") + ", or " + lastItem + "?";
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/identityFunc.mjs
function identityFunc(x) {
  return x;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/naturalCompare.mjs
function naturalCompare(aStr, bStr) {
  var aIdx = 0;
  var bIdx = 0;
  while (aIdx < aStr.length && bIdx < bStr.length) {
    var aChar = aStr.charCodeAt(aIdx);
    var bChar = bStr.charCodeAt(bIdx);
    if (isDigit(aChar) && isDigit(bChar)) {
      var aNum = 0;
      do {
        ++aIdx;
        aNum = aNum * 10 + aChar - DIGIT_0;
        aChar = aStr.charCodeAt(aIdx);
      } while (isDigit(aChar) && aNum > 0);
      var bNum = 0;
      do {
        ++bIdx;
        bNum = bNum * 10 + bChar - DIGIT_0;
        bChar = bStr.charCodeAt(bIdx);
      } while (isDigit(bChar) && bNum > 0);
      if (aNum < bNum) {
        return -1;
      }
      if (aNum > bNum) {
        return 1;
      }
    } else {
      if (aChar < bChar) {
        return -1;
      }
      if (aChar > bChar) {
        return 1;
      }
      ++aIdx;
      ++bIdx;
    }
  }
  return aStr.length - bStr.length;
}
var DIGIT_0 = 48;
var DIGIT_9 = 57;
function isDigit(code) {
  return !isNaN(code) && DIGIT_0 <= code && code <= DIGIT_9;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/suggestionList.mjs
function suggestionList(input, options) {
  var optionsByDistance = /* @__PURE__ */ Object.create(null);
  var lexicalDistance = new LexicalDistance(input);
  var threshold = Math.floor(input.length * 0.4) + 1;
  for (var _i2 = 0; _i2 < options.length; _i2++) {
    var option = options[_i2];
    var distance = lexicalDistance.measure(option, threshold);
    if (distance !== void 0) {
      optionsByDistance[option] = distance;
    }
  }
  return Object.keys(optionsByDistance).sort(function(a, b) {
    var distanceDiff = optionsByDistance[a] - optionsByDistance[b];
    return distanceDiff !== 0 ? distanceDiff : naturalCompare(a, b);
  });
}
var LexicalDistance = function() {
  function LexicalDistance2(input) {
    this._input = input;
    this._inputLowerCase = input.toLowerCase();
    this._inputArray = stringToArray(this._inputLowerCase);
    this._rows = [new Array(input.length + 1).fill(0), new Array(input.length + 1).fill(0), new Array(input.length + 1).fill(0)];
  }
  var _proto = LexicalDistance2.prototype;
  _proto.measure = function measure(option, threshold) {
    if (this._input === option) {
      return 0;
    }
    var optionLowerCase = option.toLowerCase();
    if (this._inputLowerCase === optionLowerCase) {
      return 1;
    }
    var a = stringToArray(optionLowerCase);
    var b = this._inputArray;
    if (a.length < b.length) {
      var tmp = a;
      a = b;
      b = tmp;
    }
    var aLength = a.length;
    var bLength = b.length;
    if (aLength - bLength > threshold) {
      return void 0;
    }
    var rows = this._rows;
    for (var j = 0; j <= bLength; j++) {
      rows[0][j] = j;
    }
    for (var i = 1; i <= aLength; i++) {
      var upRow = rows[(i - 1) % 3];
      var currentRow = rows[i % 3];
      var smallestCell = currentRow[0] = i;
      for (var _j = 1; _j <= bLength; _j++) {
        var cost = a[i - 1] === b[_j - 1] ? 0 : 1;
        var currentCell = Math.min(
          upRow[_j] + 1,
          // delete
          currentRow[_j - 1] + 1,
          // insert
          upRow[_j - 1] + cost
          // substitute
        );
        if (i > 1 && _j > 1 && a[i - 1] === b[_j - 2] && a[i - 2] === b[_j - 1]) {
          var doubleDiagonalCell = rows[(i - 2) % 3][_j - 2];
          currentCell = Math.min(currentCell, doubleDiagonalCell + 1);
        }
        if (currentCell < smallestCell) {
          smallestCell = currentCell;
        }
        currentRow[_j] = currentCell;
      }
      if (smallestCell > threshold) {
        return void 0;
      }
    }
    var distance = rows[aLength % 3][bLength];
    return distance <= threshold ? distance : void 0;
  };
  return LexicalDistance2;
}();
function stringToArray(str) {
  var strLength = str.length;
  var array = new Array(strLength);
  for (var i = 0; i < strLength; ++i) {
    array[i] = str.charCodeAt(i);
  }
  return array;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/printer.mjs
function print(ast) {
  return visit(ast, {
    leave: printDocASTReducer
  });
}
var MAX_LINE_LENGTH = 80;
var printDocASTReducer = {
  Name: function Name(node) {
    return node.value;
  },
  Variable: function Variable(node) {
    return "$" + node.name;
  },
  // Document
  Document: function Document(node) {
    return join(node.definitions, "\n\n") + "\n";
  },
  OperationDefinition: function OperationDefinition(node) {
    var op = node.operation;
    var name = node.name;
    var varDefs = wrap("(", join(node.variableDefinitions, ", "), ")");
    var directives = join(node.directives, " ");
    var selectionSet = node.selectionSet;
    return !name && !directives && !varDefs && op === "query" ? selectionSet : join([op, join([name, varDefs]), directives, selectionSet], " ");
  },
  VariableDefinition: function VariableDefinition(_ref) {
    var variable = _ref.variable, type = _ref.type, defaultValue = _ref.defaultValue, directives = _ref.directives;
    return variable + ": " + type + wrap(" = ", defaultValue) + wrap(" ", join(directives, " "));
  },
  SelectionSet: function SelectionSet(_ref2) {
    var selections = _ref2.selections;
    return block(selections);
  },
  Field: function Field(_ref3) {
    var alias = _ref3.alias, name = _ref3.name, args = _ref3.arguments, directives = _ref3.directives, selectionSet = _ref3.selectionSet;
    var prefix = wrap("", alias, ": ") + name;
    var argsLine = prefix + wrap("(", join(args, ", "), ")");
    if (argsLine.length > MAX_LINE_LENGTH) {
      argsLine = prefix + wrap("(\n", indent(join(args, "\n")), "\n)");
    }
    return join([argsLine, join(directives, " "), selectionSet], " ");
  },
  Argument: function Argument(_ref4) {
    var name = _ref4.name, value = _ref4.value;
    return name + ": " + value;
  },
  // Fragments
  FragmentSpread: function FragmentSpread(_ref5) {
    var name = _ref5.name, directives = _ref5.directives;
    return "..." + name + wrap(" ", join(directives, " "));
  },
  InlineFragment: function InlineFragment(_ref6) {
    var typeCondition = _ref6.typeCondition, directives = _ref6.directives, selectionSet = _ref6.selectionSet;
    return join(["...", wrap("on ", typeCondition), join(directives, " "), selectionSet], " ");
  },
  FragmentDefinition: function FragmentDefinition(_ref7) {
    var name = _ref7.name, typeCondition = _ref7.typeCondition, variableDefinitions = _ref7.variableDefinitions, directives = _ref7.directives, selectionSet = _ref7.selectionSet;
    return (
      // Note: fragment variable definitions are experimental and may be changed
      // or removed in the future.
      "fragment ".concat(name).concat(wrap("(", join(variableDefinitions, ", "), ")"), " ") + "on ".concat(typeCondition, " ").concat(wrap("", join(directives, " "), " ")) + selectionSet
    );
  },
  // Value
  IntValue: function IntValue(_ref8) {
    var value = _ref8.value;
    return value;
  },
  FloatValue: function FloatValue(_ref9) {
    var value = _ref9.value;
    return value;
  },
  StringValue: function StringValue(_ref10, key) {
    var value = _ref10.value, isBlockString = _ref10.block;
    return isBlockString ? printBlockString(value, key === "description" ? "" : "  ") : JSON.stringify(value);
  },
  BooleanValue: function BooleanValue(_ref11) {
    var value = _ref11.value;
    return value ? "true" : "false";
  },
  NullValue: function NullValue() {
    return "null";
  },
  EnumValue: function EnumValue(_ref12) {
    var value = _ref12.value;
    return value;
  },
  ListValue: function ListValue(_ref13) {
    var values = _ref13.values;
    return "[" + join(values, ", ") + "]";
  },
  ObjectValue: function ObjectValue(_ref14) {
    var fields7 = _ref14.fields;
    return "{" + join(fields7, ", ") + "}";
  },
  ObjectField: function ObjectField(_ref15) {
    var name = _ref15.name, value = _ref15.value;
    return name + ": " + value;
  },
  // Directive
  Directive: function Directive(_ref16) {
    var name = _ref16.name, args = _ref16.arguments;
    return "@" + name + wrap("(", join(args, ", "), ")");
  },
  // Type
  NamedType: function NamedType(_ref17) {
    var name = _ref17.name;
    return name;
  },
  ListType: function ListType(_ref18) {
    var type = _ref18.type;
    return "[" + type + "]";
  },
  NonNullType: function NonNullType(_ref19) {
    var type = _ref19.type;
    return type + "!";
  },
  // Type System Definitions
  SchemaDefinition: addDescription(function(_ref20) {
    var directives = _ref20.directives, operationTypes = _ref20.operationTypes;
    return join(["schema", join(directives, " "), block(operationTypes)], " ");
  }),
  OperationTypeDefinition: function OperationTypeDefinition(_ref21) {
    var operation = _ref21.operation, type = _ref21.type;
    return operation + ": " + type;
  },
  ScalarTypeDefinition: addDescription(function(_ref22) {
    var name = _ref22.name, directives = _ref22.directives;
    return join(["scalar", name, join(directives, " ")], " ");
  }),
  ObjectTypeDefinition: addDescription(function(_ref23) {
    var name = _ref23.name, interfaces = _ref23.interfaces, directives = _ref23.directives, fields7 = _ref23.fields;
    return join(["type", name, wrap("implements ", join(interfaces, " & ")), join(directives, " "), block(fields7)], " ");
  }),
  FieldDefinition: addDescription(function(_ref24) {
    var name = _ref24.name, args = _ref24.arguments, type = _ref24.type, directives = _ref24.directives;
    return name + (hasMultilineItems(args) ? wrap("(\n", indent(join(args, "\n")), "\n)") : wrap("(", join(args, ", "), ")")) + ": " + type + wrap(" ", join(directives, " "));
  }),
  InputValueDefinition: addDescription(function(_ref25) {
    var name = _ref25.name, type = _ref25.type, defaultValue = _ref25.defaultValue, directives = _ref25.directives;
    return join([name + ": " + type, wrap("= ", defaultValue), join(directives, " ")], " ");
  }),
  InterfaceTypeDefinition: addDescription(function(_ref26) {
    var name = _ref26.name, interfaces = _ref26.interfaces, directives = _ref26.directives, fields7 = _ref26.fields;
    return join(["interface", name, wrap("implements ", join(interfaces, " & ")), join(directives, " "), block(fields7)], " ");
  }),
  UnionTypeDefinition: addDescription(function(_ref27) {
    var name = _ref27.name, directives = _ref27.directives, types = _ref27.types;
    return join(["union", name, join(directives, " "), types && types.length !== 0 ? "= " + join(types, " | ") : ""], " ");
  }),
  EnumTypeDefinition: addDescription(function(_ref28) {
    var name = _ref28.name, directives = _ref28.directives, values = _ref28.values;
    return join(["enum", name, join(directives, " "), block(values)], " ");
  }),
  EnumValueDefinition: addDescription(function(_ref29) {
    var name = _ref29.name, directives = _ref29.directives;
    return join([name, join(directives, " ")], " ");
  }),
  InputObjectTypeDefinition: addDescription(function(_ref30) {
    var name = _ref30.name, directives = _ref30.directives, fields7 = _ref30.fields;
    return join(["input", name, join(directives, " "), block(fields7)], " ");
  }),
  DirectiveDefinition: addDescription(function(_ref31) {
    var name = _ref31.name, args = _ref31.arguments, repeatable = _ref31.repeatable, locations = _ref31.locations;
    return "directive @" + name + (hasMultilineItems(args) ? wrap("(\n", indent(join(args, "\n")), "\n)") : wrap("(", join(args, ", "), ")")) + (repeatable ? " repeatable" : "") + " on " + join(locations, " | ");
  }),
  SchemaExtension: function SchemaExtension(_ref32) {
    var directives = _ref32.directives, operationTypes = _ref32.operationTypes;
    return join(["extend schema", join(directives, " "), block(operationTypes)], " ");
  },
  ScalarTypeExtension: function ScalarTypeExtension(_ref33) {
    var name = _ref33.name, directives = _ref33.directives;
    return join(["extend scalar", name, join(directives, " ")], " ");
  },
  ObjectTypeExtension: function ObjectTypeExtension(_ref34) {
    var name = _ref34.name, interfaces = _ref34.interfaces, directives = _ref34.directives, fields7 = _ref34.fields;
    return join(["extend type", name, wrap("implements ", join(interfaces, " & ")), join(directives, " "), block(fields7)], " ");
  },
  InterfaceTypeExtension: function InterfaceTypeExtension(_ref35) {
    var name = _ref35.name, interfaces = _ref35.interfaces, directives = _ref35.directives, fields7 = _ref35.fields;
    return join(["extend interface", name, wrap("implements ", join(interfaces, " & ")), join(directives, " "), block(fields7)], " ");
  },
  UnionTypeExtension: function UnionTypeExtension(_ref36) {
    var name = _ref36.name, directives = _ref36.directives, types = _ref36.types;
    return join(["extend union", name, join(directives, " "), types && types.length !== 0 ? "= " + join(types, " | ") : ""], " ");
  },
  EnumTypeExtension: function EnumTypeExtension(_ref37) {
    var name = _ref37.name, directives = _ref37.directives, values = _ref37.values;
    return join(["extend enum", name, join(directives, " "), block(values)], " ");
  },
  InputObjectTypeExtension: function InputObjectTypeExtension(_ref38) {
    var name = _ref38.name, directives = _ref38.directives, fields7 = _ref38.fields;
    return join(["extend input", name, join(directives, " "), block(fields7)], " ");
  }
};
function addDescription(cb) {
  return function(node) {
    return join([node.description, cb(node)], "\n");
  };
}
function join(maybeArray) {
  var _maybeArray$filter$jo;
  var separator = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : "";
  return (_maybeArray$filter$jo = maybeArray === null || maybeArray === void 0 ? void 0 : maybeArray.filter(function(x) {
    return x;
  }).join(separator)) !== null && _maybeArray$filter$jo !== void 0 ? _maybeArray$filter$jo : "";
}
function block(array) {
  return wrap("{\n", indent(join(array, "\n")), "\n}");
}
function wrap(start, maybeString) {
  var end = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : "";
  return maybeString != null && maybeString !== "" ? start + maybeString + end : "";
}
function indent(str) {
  return wrap("  ", str.replace(/\n/g, "\n  "));
}
function isMultiline(str) {
  return str.indexOf("\n") !== -1;
}
function hasMultilineItems(maybeArray) {
  return maybeArray != null && maybeArray.some(isMultiline);
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/valueFromASTUntyped.mjs
function valueFromASTUntyped(valueNode, variables) {
  switch (valueNode.kind) {
    case Kind.NULL:
      return null;
    case Kind.INT:
      return parseInt(valueNode.value, 10);
    case Kind.FLOAT:
      return parseFloat(valueNode.value);
    case Kind.STRING:
    case Kind.ENUM:
    case Kind.BOOLEAN:
      return valueNode.value;
    case Kind.LIST:
      return valueNode.values.map(function(node) {
        return valueFromASTUntyped(node, variables);
      });
    case Kind.OBJECT:
      return keyValMap(valueNode.fields, function(field) {
        return field.name.value;
      }, function(field) {
        return valueFromASTUntyped(field.value, variables);
      });
    case Kind.VARIABLE:
      return variables === null || variables === void 0 ? void 0 : variables[valueNode.name.value];
  }
  invariant(0, "Unexpected value node: " + inspect(valueNode));
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/type/definition.mjs
function _defineProperties3(target, props) {
  for (var i = 0; i < props.length; i++) {
    var descriptor = props[i];
    descriptor.enumerable = descriptor.enumerable || false;
    descriptor.configurable = true;
    if ("value" in descriptor) descriptor.writable = true;
    Object.defineProperty(target, descriptor.key, descriptor);
  }
}
function _createClass3(Constructor, protoProps, staticProps) {
  if (protoProps) _defineProperties3(Constructor.prototype, protoProps);
  if (staticProps) _defineProperties3(Constructor, staticProps);
  return Constructor;
}
function isType(type) {
  return isScalarType(type) || isObjectType(type) || isInterfaceType(type) || isUnionType(type) || isEnumType(type) || isInputObjectType(type) || isListType(type) || isNonNullType(type);
}
function assertType(type) {
  if (!isType(type)) {
    throw new Error("Expected ".concat(inspect(type), " to be a GraphQL type."));
  }
  return type;
}
function isScalarType(type) {
  return instanceOf_default(type, GraphQLScalarType);
}
function isObjectType(type) {
  return instanceOf_default(type, GraphQLObjectType);
}
function isInterfaceType(type) {
  return instanceOf_default(type, GraphQLInterfaceType);
}
function isUnionType(type) {
  return instanceOf_default(type, GraphQLUnionType);
}
function isEnumType(type) {
  return instanceOf_default(type, GraphQLEnumType);
}
function isInputObjectType(type) {
  return instanceOf_default(type, GraphQLInputObjectType);
}
function isListType(type) {
  return instanceOf_default(type, GraphQLList);
}
function isNonNullType(type) {
  return instanceOf_default(type, GraphQLNonNull);
}
function isInputType(type) {
  return isScalarType(type) || isEnumType(type) || isInputObjectType(type) || isWrappingType(type) && isInputType(type.ofType);
}
function isOutputType(type) {
  return isScalarType(type) || isObjectType(type) || isInterfaceType(type) || isUnionType(type) || isEnumType(type) || isWrappingType(type) && isOutputType(type.ofType);
}
function isLeafType(type) {
  return isScalarType(type) || isEnumType(type);
}
function isCompositeType(type) {
  return isObjectType(type) || isInterfaceType(type) || isUnionType(type);
}
function isAbstractType(type) {
  return isInterfaceType(type) || isUnionType(type);
}
function GraphQLList(ofType) {
  if (this instanceof GraphQLList) {
    this.ofType = assertType(ofType);
  } else {
    return new GraphQLList(ofType);
  }
}
GraphQLList.prototype.toString = function toString() {
  return "[" + String(this.ofType) + "]";
};
GraphQLList.prototype.toJSON = function toJSON() {
  return this.toString();
};
Object.defineProperty(GraphQLList.prototype, SYMBOL_TO_STRING_TAG, {
  get: function get() {
    return "GraphQLList";
  }
});
defineInspect(GraphQLList);
function GraphQLNonNull(ofType) {
  if (this instanceof GraphQLNonNull) {
    this.ofType = assertNullableType(ofType);
  } else {
    return new GraphQLNonNull(ofType);
  }
}
GraphQLNonNull.prototype.toString = function toString2() {
  return String(this.ofType) + "!";
};
GraphQLNonNull.prototype.toJSON = function toJSON2() {
  return this.toString();
};
Object.defineProperty(GraphQLNonNull.prototype, SYMBOL_TO_STRING_TAG, {
  get: function get2() {
    return "GraphQLNonNull";
  }
});
defineInspect(GraphQLNonNull);
function isWrappingType(type) {
  return isListType(type) || isNonNullType(type);
}
function isNullableType(type) {
  return isType(type) && !isNonNullType(type);
}
function assertNullableType(type) {
  if (!isNullableType(type)) {
    throw new Error("Expected ".concat(inspect(type), " to be a GraphQL nullable type."));
  }
  return type;
}
function getNullableType(type) {
  if (type) {
    return isNonNullType(type) ? type.ofType : type;
  }
}
function getNamedType(type) {
  if (type) {
    var unwrappedType = type;
    while (isWrappingType(unwrappedType)) {
      unwrappedType = unwrappedType.ofType;
    }
    return unwrappedType;
  }
}
function resolveThunk(thunk) {
  return typeof thunk === "function" ? thunk() : thunk;
}
function undefineIfEmpty(arr) {
  return arr && arr.length > 0 ? arr : void 0;
}
var GraphQLScalarType = function() {
  function GraphQLScalarType2(config) {
    var _config$parseValue, _config$serialize, _config$parseLiteral;
    var parseValue2 = (_config$parseValue = config.parseValue) !== null && _config$parseValue !== void 0 ? _config$parseValue : identityFunc;
    this.name = config.name;
    this.description = config.description;
    this.specifiedByUrl = config.specifiedByUrl;
    this.serialize = (_config$serialize = config.serialize) !== null && _config$serialize !== void 0 ? _config$serialize : identityFunc;
    this.parseValue = parseValue2;
    this.parseLiteral = (_config$parseLiteral = config.parseLiteral) !== null && _config$parseLiteral !== void 0 ? _config$parseLiteral : function(node, variables) {
      return parseValue2(valueFromASTUntyped(node, variables));
    };
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    this.extensionASTNodes = undefineIfEmpty(config.extensionASTNodes);
    typeof config.name === "string" || devAssert(0, "Must provide name.");
    config.specifiedByUrl == null || typeof config.specifiedByUrl === "string" || devAssert(0, "".concat(this.name, ' must provide "specifiedByUrl" as a string, ') + "but got: ".concat(inspect(config.specifiedByUrl), "."));
    config.serialize == null || typeof config.serialize === "function" || devAssert(0, "".concat(this.name, ' must provide "serialize" function. If this custom Scalar is also used as an input type, ensure "parseValue" and "parseLiteral" functions are also provided.'));
    if (config.parseLiteral) {
      typeof config.parseValue === "function" && typeof config.parseLiteral === "function" || devAssert(0, "".concat(this.name, ' must provide both "parseValue" and "parseLiteral" functions.'));
    }
  }
  var _proto = GraphQLScalarType2.prototype;
  _proto.toConfig = function toConfig() {
    var _this$extensionASTNod;
    return {
      name: this.name,
      description: this.description,
      specifiedByUrl: this.specifiedByUrl,
      serialize: this.serialize,
      parseValue: this.parseValue,
      parseLiteral: this.parseLiteral,
      extensions: this.extensions,
      astNode: this.astNode,
      extensionASTNodes: (_this$extensionASTNod = this.extensionASTNodes) !== null && _this$extensionASTNod !== void 0 ? _this$extensionASTNod : []
    };
  };
  _proto.toString = function toString3() {
    return this.name;
  };
  _proto.toJSON = function toJSON3() {
    return this.toString();
  };
  _createClass3(GraphQLScalarType2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLScalarType";
    }
  }]);
  return GraphQLScalarType2;
}();
defineInspect(GraphQLScalarType);
var GraphQLObjectType = function() {
  function GraphQLObjectType2(config) {
    this.name = config.name;
    this.description = config.description;
    this.isTypeOf = config.isTypeOf;
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    this.extensionASTNodes = undefineIfEmpty(config.extensionASTNodes);
    this._fields = defineFieldMap.bind(void 0, config);
    this._interfaces = defineInterfaces.bind(void 0, config);
    typeof config.name === "string" || devAssert(0, "Must provide name.");
    config.isTypeOf == null || typeof config.isTypeOf === "function" || devAssert(0, "".concat(this.name, ' must provide "isTypeOf" as a function, ') + "but got: ".concat(inspect(config.isTypeOf), "."));
  }
  var _proto2 = GraphQLObjectType2.prototype;
  _proto2.getFields = function getFields() {
    if (typeof this._fields === "function") {
      this._fields = this._fields();
    }
    return this._fields;
  };
  _proto2.getInterfaces = function getInterfaces() {
    if (typeof this._interfaces === "function") {
      this._interfaces = this._interfaces();
    }
    return this._interfaces;
  };
  _proto2.toConfig = function toConfig() {
    return {
      name: this.name,
      description: this.description,
      interfaces: this.getInterfaces(),
      fields: fieldsToFieldsConfig(this.getFields()),
      isTypeOf: this.isTypeOf,
      extensions: this.extensions,
      astNode: this.astNode,
      extensionASTNodes: this.extensionASTNodes || []
    };
  };
  _proto2.toString = function toString3() {
    return this.name;
  };
  _proto2.toJSON = function toJSON3() {
    return this.toString();
  };
  _createClass3(GraphQLObjectType2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLObjectType";
    }
  }]);
  return GraphQLObjectType2;
}();
defineInspect(GraphQLObjectType);
function defineInterfaces(config) {
  var _resolveThunk;
  var interfaces = (_resolveThunk = resolveThunk(config.interfaces)) !== null && _resolveThunk !== void 0 ? _resolveThunk : [];
  Array.isArray(interfaces) || devAssert(0, "".concat(config.name, " interfaces must be an Array or a function which returns an Array."));
  return interfaces;
}
function defineFieldMap(config) {
  var fieldMap = resolveThunk(config.fields);
  isPlainObj(fieldMap) || devAssert(0, "".concat(config.name, " fields must be an object with field names as keys or a function which returns such an object."));
  return mapValue(fieldMap, function(fieldConfig, fieldName) {
    var _fieldConfig$args;
    isPlainObj(fieldConfig) || devAssert(0, "".concat(config.name, ".").concat(fieldName, " field config must be an object."));
    !("isDeprecated" in fieldConfig) || devAssert(0, "".concat(config.name, ".").concat(fieldName, ' should provide "deprecationReason" instead of "isDeprecated".'));
    fieldConfig.resolve == null || typeof fieldConfig.resolve === "function" || devAssert(0, "".concat(config.name, ".").concat(fieldName, " field resolver must be a function if ") + "provided, but got: ".concat(inspect(fieldConfig.resolve), "."));
    var argsConfig = (_fieldConfig$args = fieldConfig.args) !== null && _fieldConfig$args !== void 0 ? _fieldConfig$args : {};
    isPlainObj(argsConfig) || devAssert(0, "".concat(config.name, ".").concat(fieldName, " args must be an object with argument names as keys."));
    var args = objectEntries_default(argsConfig).map(function(_ref) {
      var argName = _ref[0], argConfig = _ref[1];
      return {
        name: argName,
        description: argConfig.description,
        type: argConfig.type,
        defaultValue: argConfig.defaultValue,
        deprecationReason: argConfig.deprecationReason,
        extensions: argConfig.extensions && toObjMap(argConfig.extensions),
        astNode: argConfig.astNode
      };
    });
    return {
      name: fieldName,
      description: fieldConfig.description,
      type: fieldConfig.type,
      args,
      resolve: fieldConfig.resolve,
      subscribe: fieldConfig.subscribe,
      isDeprecated: fieldConfig.deprecationReason != null,
      deprecationReason: fieldConfig.deprecationReason,
      extensions: fieldConfig.extensions && toObjMap(fieldConfig.extensions),
      astNode: fieldConfig.astNode
    };
  });
}
function isPlainObj(obj) {
  return isObjectLike(obj) && !Array.isArray(obj);
}
function fieldsToFieldsConfig(fields7) {
  return mapValue(fields7, function(field) {
    return {
      description: field.description,
      type: field.type,
      args: argsToArgsConfig(field.args),
      resolve: field.resolve,
      subscribe: field.subscribe,
      deprecationReason: field.deprecationReason,
      extensions: field.extensions,
      astNode: field.astNode
    };
  });
}
function argsToArgsConfig(args) {
  return keyValMap(args, function(arg) {
    return arg.name;
  }, function(arg) {
    return {
      description: arg.description,
      type: arg.type,
      defaultValue: arg.defaultValue,
      deprecationReason: arg.deprecationReason,
      extensions: arg.extensions,
      astNode: arg.astNode
    };
  });
}
function isRequiredArgument(arg) {
  return isNonNullType(arg.type) && arg.defaultValue === void 0;
}
var GraphQLInterfaceType = function() {
  function GraphQLInterfaceType2(config) {
    this.name = config.name;
    this.description = config.description;
    this.resolveType = config.resolveType;
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    this.extensionASTNodes = undefineIfEmpty(config.extensionASTNodes);
    this._fields = defineFieldMap.bind(void 0, config);
    this._interfaces = defineInterfaces.bind(void 0, config);
    typeof config.name === "string" || devAssert(0, "Must provide name.");
    config.resolveType == null || typeof config.resolveType === "function" || devAssert(0, "".concat(this.name, ' must provide "resolveType" as a function, ') + "but got: ".concat(inspect(config.resolveType), "."));
  }
  var _proto3 = GraphQLInterfaceType2.prototype;
  _proto3.getFields = function getFields() {
    if (typeof this._fields === "function") {
      this._fields = this._fields();
    }
    return this._fields;
  };
  _proto3.getInterfaces = function getInterfaces() {
    if (typeof this._interfaces === "function") {
      this._interfaces = this._interfaces();
    }
    return this._interfaces;
  };
  _proto3.toConfig = function toConfig() {
    var _this$extensionASTNod2;
    return {
      name: this.name,
      description: this.description,
      interfaces: this.getInterfaces(),
      fields: fieldsToFieldsConfig(this.getFields()),
      resolveType: this.resolveType,
      extensions: this.extensions,
      astNode: this.astNode,
      extensionASTNodes: (_this$extensionASTNod2 = this.extensionASTNodes) !== null && _this$extensionASTNod2 !== void 0 ? _this$extensionASTNod2 : []
    };
  };
  _proto3.toString = function toString3() {
    return this.name;
  };
  _proto3.toJSON = function toJSON3() {
    return this.toString();
  };
  _createClass3(GraphQLInterfaceType2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLInterfaceType";
    }
  }]);
  return GraphQLInterfaceType2;
}();
defineInspect(GraphQLInterfaceType);
var GraphQLUnionType = function() {
  function GraphQLUnionType2(config) {
    this.name = config.name;
    this.description = config.description;
    this.resolveType = config.resolveType;
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    this.extensionASTNodes = undefineIfEmpty(config.extensionASTNodes);
    this._types = defineTypes.bind(void 0, config);
    typeof config.name === "string" || devAssert(0, "Must provide name.");
    config.resolveType == null || typeof config.resolveType === "function" || devAssert(0, "".concat(this.name, ' must provide "resolveType" as a function, ') + "but got: ".concat(inspect(config.resolveType), "."));
  }
  var _proto4 = GraphQLUnionType2.prototype;
  _proto4.getTypes = function getTypes() {
    if (typeof this._types === "function") {
      this._types = this._types();
    }
    return this._types;
  };
  _proto4.toConfig = function toConfig() {
    var _this$extensionASTNod3;
    return {
      name: this.name,
      description: this.description,
      types: this.getTypes(),
      resolveType: this.resolveType,
      extensions: this.extensions,
      astNode: this.astNode,
      extensionASTNodes: (_this$extensionASTNod3 = this.extensionASTNodes) !== null && _this$extensionASTNod3 !== void 0 ? _this$extensionASTNod3 : []
    };
  };
  _proto4.toString = function toString3() {
    return this.name;
  };
  _proto4.toJSON = function toJSON3() {
    return this.toString();
  };
  _createClass3(GraphQLUnionType2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLUnionType";
    }
  }]);
  return GraphQLUnionType2;
}();
defineInspect(GraphQLUnionType);
function defineTypes(config) {
  var types = resolveThunk(config.types);
  Array.isArray(types) || devAssert(0, "Must provide Array of types or a function which returns such an array for Union ".concat(config.name, "."));
  return types;
}
var GraphQLEnumType = function() {
  function GraphQLEnumType2(config) {
    this.name = config.name;
    this.description = config.description;
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    this.extensionASTNodes = undefineIfEmpty(config.extensionASTNodes);
    this._values = defineEnumValues(this.name, config.values);
    this._valueLookup = new Map(this._values.map(function(enumValue) {
      return [enumValue.value, enumValue];
    }));
    this._nameLookup = keyMap(this._values, function(value) {
      return value.name;
    });
    typeof config.name === "string" || devAssert(0, "Must provide name.");
  }
  var _proto5 = GraphQLEnumType2.prototype;
  _proto5.getValues = function getValues() {
    return this._values;
  };
  _proto5.getValue = function getValue(name) {
    return this._nameLookup[name];
  };
  _proto5.serialize = function serialize(outputValue) {
    var enumValue = this._valueLookup.get(outputValue);
    if (enumValue === void 0) {
      throw new GraphQLError('Enum "'.concat(this.name, '" cannot represent value: ').concat(inspect(outputValue)));
    }
    return enumValue.name;
  };
  _proto5.parseValue = function parseValue2(inputValue) {
    if (typeof inputValue !== "string") {
      var valueStr = inspect(inputValue);
      throw new GraphQLError('Enum "'.concat(this.name, '" cannot represent non-string value: ').concat(valueStr, ".") + didYouMeanEnumValue(this, valueStr));
    }
    var enumValue = this.getValue(inputValue);
    if (enumValue == null) {
      throw new GraphQLError('Value "'.concat(inputValue, '" does not exist in "').concat(this.name, '" enum.') + didYouMeanEnumValue(this, inputValue));
    }
    return enumValue.value;
  };
  _proto5.parseLiteral = function parseLiteral6(valueNode, _variables) {
    if (valueNode.kind !== Kind.ENUM) {
      var valueStr = print(valueNode);
      throw new GraphQLError('Enum "'.concat(this.name, '" cannot represent non-enum value: ').concat(valueStr, ".") + didYouMeanEnumValue(this, valueStr), valueNode);
    }
    var enumValue = this.getValue(valueNode.value);
    if (enumValue == null) {
      var _valueStr = print(valueNode);
      throw new GraphQLError('Value "'.concat(_valueStr, '" does not exist in "').concat(this.name, '" enum.') + didYouMeanEnumValue(this, _valueStr), valueNode);
    }
    return enumValue.value;
  };
  _proto5.toConfig = function toConfig() {
    var _this$extensionASTNod4;
    var values = keyValMap(this.getValues(), function(value) {
      return value.name;
    }, function(value) {
      return {
        description: value.description,
        value: value.value,
        deprecationReason: value.deprecationReason,
        extensions: value.extensions,
        astNode: value.astNode
      };
    });
    return {
      name: this.name,
      description: this.description,
      values,
      extensions: this.extensions,
      astNode: this.astNode,
      extensionASTNodes: (_this$extensionASTNod4 = this.extensionASTNodes) !== null && _this$extensionASTNod4 !== void 0 ? _this$extensionASTNod4 : []
    };
  };
  _proto5.toString = function toString3() {
    return this.name;
  };
  _proto5.toJSON = function toJSON3() {
    return this.toString();
  };
  _createClass3(GraphQLEnumType2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLEnumType";
    }
  }]);
  return GraphQLEnumType2;
}();
defineInspect(GraphQLEnumType);
function didYouMeanEnumValue(enumType, unknownValueStr) {
  var allNames = enumType.getValues().map(function(value) {
    return value.name;
  });
  var suggestedValues = suggestionList(unknownValueStr, allNames);
  return didYouMean("the enum value", suggestedValues);
}
function defineEnumValues(typeName, valueMap) {
  isPlainObj(valueMap) || devAssert(0, "".concat(typeName, " values must be an object with value names as keys."));
  return objectEntries_default(valueMap).map(function(_ref2) {
    var valueName = _ref2[0], valueConfig = _ref2[1];
    isPlainObj(valueConfig) || devAssert(0, "".concat(typeName, ".").concat(valueName, ' must refer to an object with a "value" key ') + "representing an internal value but got: ".concat(inspect(valueConfig), "."));
    !("isDeprecated" in valueConfig) || devAssert(0, "".concat(typeName, ".").concat(valueName, ' should provide "deprecationReason" instead of "isDeprecated".'));
    return {
      name: valueName,
      description: valueConfig.description,
      value: valueConfig.value !== void 0 ? valueConfig.value : valueName,
      isDeprecated: valueConfig.deprecationReason != null,
      deprecationReason: valueConfig.deprecationReason,
      extensions: valueConfig.extensions && toObjMap(valueConfig.extensions),
      astNode: valueConfig.astNode
    };
  });
}
var GraphQLInputObjectType = function() {
  function GraphQLInputObjectType2(config) {
    this.name = config.name;
    this.description = config.description;
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    this.extensionASTNodes = undefineIfEmpty(config.extensionASTNodes);
    this._fields = defineInputFieldMap.bind(void 0, config);
    typeof config.name === "string" || devAssert(0, "Must provide name.");
  }
  var _proto6 = GraphQLInputObjectType2.prototype;
  _proto6.getFields = function getFields() {
    if (typeof this._fields === "function") {
      this._fields = this._fields();
    }
    return this._fields;
  };
  _proto6.toConfig = function toConfig() {
    var _this$extensionASTNod5;
    var fields7 = mapValue(this.getFields(), function(field) {
      return {
        description: field.description,
        type: field.type,
        defaultValue: field.defaultValue,
        deprecationReason: field.deprecationReason,
        extensions: field.extensions,
        astNode: field.astNode
      };
    });
    return {
      name: this.name,
      description: this.description,
      fields: fields7,
      extensions: this.extensions,
      astNode: this.astNode,
      extensionASTNodes: (_this$extensionASTNod5 = this.extensionASTNodes) !== null && _this$extensionASTNod5 !== void 0 ? _this$extensionASTNod5 : []
    };
  };
  _proto6.toString = function toString3() {
    return this.name;
  };
  _proto6.toJSON = function toJSON3() {
    return this.toString();
  };
  _createClass3(GraphQLInputObjectType2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLInputObjectType";
    }
  }]);
  return GraphQLInputObjectType2;
}();
defineInspect(GraphQLInputObjectType);
function defineInputFieldMap(config) {
  var fieldMap = resolveThunk(config.fields);
  isPlainObj(fieldMap) || devAssert(0, "".concat(config.name, " fields must be an object with field names as keys or a function which returns such an object."));
  return mapValue(fieldMap, function(fieldConfig, fieldName) {
    !("resolve" in fieldConfig) || devAssert(0, "".concat(config.name, ".").concat(fieldName, " field has a resolve property, but Input Types cannot define resolvers."));
    return {
      name: fieldName,
      description: fieldConfig.description,
      type: fieldConfig.type,
      defaultValue: fieldConfig.defaultValue,
      deprecationReason: fieldConfig.deprecationReason,
      extensions: fieldConfig.extensions && toObjMap(fieldConfig.extensions),
      astNode: fieldConfig.astNode
    };
  });
}
function isRequiredInputField(field) {
  return isNonNullType(field.type) && field.defaultValue === void 0;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/typeComparators.mjs
function isTypeSubTypeOf(schema, maybeSubType, superType) {
  if (maybeSubType === superType) {
    return true;
  }
  if (isNonNullType(superType)) {
    if (isNonNullType(maybeSubType)) {
      return isTypeSubTypeOf(schema, maybeSubType.ofType, superType.ofType);
    }
    return false;
  }
  if (isNonNullType(maybeSubType)) {
    return isTypeSubTypeOf(schema, maybeSubType.ofType, superType);
  }
  if (isListType(superType)) {
    if (isListType(maybeSubType)) {
      return isTypeSubTypeOf(schema, maybeSubType.ofType, superType.ofType);
    }
    return false;
  }
  if (isListType(maybeSubType)) {
    return false;
  }
  return isAbstractType(superType) && (isInterfaceType(maybeSubType) || isObjectType(maybeSubType)) && schema.isSubType(superType, maybeSubType);
}
function doTypesOverlap(schema, typeA, typeB) {
  if (typeA === typeB) {
    return true;
  }
  if (isAbstractType(typeA)) {
    if (isAbstractType(typeB)) {
      return schema.getPossibleTypes(typeA).some(function(type) {
        return schema.isSubType(typeB, type);
      });
    }
    return schema.isSubType(typeA, typeB);
  }
  if (isAbstractType(typeB)) {
    return schema.isSubType(typeB, typeA);
  }
  return false;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/polyfills/arrayFrom.mjs
var arrayFrom = Array.from || function(obj, mapFn, thisArg) {
  if (obj == null) {
    throw new TypeError("Array.from requires an array-like object - not null or undefined");
  }
  var iteratorMethod = obj[SYMBOL_ITERATOR];
  if (typeof iteratorMethod === "function") {
    var iterator = iteratorMethod.call(obj);
    var result = [];
    var step;
    for (var i = 0; !(step = iterator.next()).done; ++i) {
      result.push(mapFn.call(thisArg, step.value, i));
      if (i > 9999999) {
        throw new TypeError("Near-infinite iteration.");
      }
    }
    return result;
  }
  var length = obj.length;
  if (typeof length === "number" && length >= 0 && length % 1 === 0) {
    var _result = [];
    for (var _i = 0; _i < length; ++_i) {
      if (Object.prototype.hasOwnProperty.call(obj, _i)) {
        _result.push(mapFn.call(thisArg, obj[_i], _i));
      }
    }
    return _result;
  }
  return [];
};
var arrayFrom_default = arrayFrom;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/polyfills/isFinite.mjs
var isFinitePolyfill = Number.isFinite || function(value) {
  return typeof value === "number" && isFinite(value);
};
var isFinite_default = isFinitePolyfill;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/safeArrayFrom.mjs
function _typeof5(obj) {
  "@babel/helpers - typeof";
  if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") {
    _typeof5 = function _typeof6(obj2) {
      return typeof obj2;
    };
  } else {
    _typeof5 = function _typeof6(obj2) {
      return obj2 && typeof Symbol === "function" && obj2.constructor === Symbol && obj2 !== Symbol.prototype ? "symbol" : typeof obj2;
    };
  }
  return _typeof5(obj);
}
function safeArrayFrom(collection) {
  var mapFn = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : function(item) {
    return item;
  };
  if (collection == null || _typeof5(collection) !== "object") {
    return null;
  }
  if (Array.isArray(collection)) {
    return collection.map(mapFn);
  }
  var iteratorMethod = collection[SYMBOL_ITERATOR];
  if (typeof iteratorMethod === "function") {
    var iterator = iteratorMethod.call(collection);
    var result = [];
    var step;
    for (var i = 0; !(step = iterator.next()).done; ++i) {
      result.push(mapFn(step.value, i));
    }
    return result;
  }
  var length = collection.length;
  if (typeof length === "number" && length >= 0 && length % 1 === 0) {
    var _result = [];
    for (var _i = 0; _i < length; ++_i) {
      if (!Object.prototype.hasOwnProperty.call(collection, _i)) {
        return null;
      }
      _result.push(mapFn(collection[String(_i)], _i));
    }
    return _result;
  }
  return null;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/polyfills/isInteger.mjs
var isInteger = Number.isInteger || function(value) {
  return typeof value === "number" && isFinite(value) && Math.floor(value) === value;
};
var isInteger_default = isInteger;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/type/scalars.mjs
var MAX_INT = 2147483647;
var MIN_INT = -2147483648;
function serializeInt(outputValue) {
  var coercedValue = serializeObject(outputValue);
  if (typeof coercedValue === "boolean") {
    return coercedValue ? 1 : 0;
  }
  var num = coercedValue;
  if (typeof coercedValue === "string" && coercedValue !== "") {
    num = Number(coercedValue);
  }
  if (!isInteger_default(num)) {
    throw new GraphQLError("Int cannot represent non-integer value: ".concat(inspect(coercedValue)));
  }
  if (num > MAX_INT || num < MIN_INT) {
    throw new GraphQLError("Int cannot represent non 32-bit signed integer value: " + inspect(coercedValue));
  }
  return num;
}
function coerceInt(inputValue) {
  if (!isInteger_default(inputValue)) {
    throw new GraphQLError("Int cannot represent non-integer value: ".concat(inspect(inputValue)));
  }
  if (inputValue > MAX_INT || inputValue < MIN_INT) {
    throw new GraphQLError("Int cannot represent non 32-bit signed integer value: ".concat(inputValue));
  }
  return inputValue;
}
var GraphQLInt = new GraphQLScalarType({
  name: "Int",
  description: "The `Int` scalar type represents non-fractional signed whole numeric values. Int can represent values between -(2^31) and 2^31 - 1.",
  serialize: serializeInt,
  parseValue: coerceInt,
  parseLiteral: function parseLiteral(valueNode) {
    if (valueNode.kind !== Kind.INT) {
      throw new GraphQLError("Int cannot represent non-integer value: ".concat(print(valueNode)), valueNode);
    }
    var num = parseInt(valueNode.value, 10);
    if (num > MAX_INT || num < MIN_INT) {
      throw new GraphQLError("Int cannot represent non 32-bit signed integer value: ".concat(valueNode.value), valueNode);
    }
    return num;
  }
});
function serializeFloat(outputValue) {
  var coercedValue = serializeObject(outputValue);
  if (typeof coercedValue === "boolean") {
    return coercedValue ? 1 : 0;
  }
  var num = coercedValue;
  if (typeof coercedValue === "string" && coercedValue !== "") {
    num = Number(coercedValue);
  }
  if (!isFinite_default(num)) {
    throw new GraphQLError("Float cannot represent non numeric value: ".concat(inspect(coercedValue)));
  }
  return num;
}
function coerceFloat(inputValue) {
  if (!isFinite_default(inputValue)) {
    throw new GraphQLError("Float cannot represent non numeric value: ".concat(inspect(inputValue)));
  }
  return inputValue;
}
var GraphQLFloat = new GraphQLScalarType({
  name: "Float",
  description: "The `Float` scalar type represents signed double-precision fractional values as specified by [IEEE 754](https://en.wikipedia.org/wiki/IEEE_floating_point).",
  serialize: serializeFloat,
  parseValue: coerceFloat,
  parseLiteral: function parseLiteral2(valueNode) {
    if (valueNode.kind !== Kind.FLOAT && valueNode.kind !== Kind.INT) {
      throw new GraphQLError("Float cannot represent non numeric value: ".concat(print(valueNode)), valueNode);
    }
    return parseFloat(valueNode.value);
  }
});
function serializeObject(outputValue) {
  if (isObjectLike(outputValue)) {
    if (typeof outputValue.valueOf === "function") {
      var valueOfResult = outputValue.valueOf();
      if (!isObjectLike(valueOfResult)) {
        return valueOfResult;
      }
    }
    if (typeof outputValue.toJSON === "function") {
      return outputValue.toJSON();
    }
  }
  return outputValue;
}
function serializeString(outputValue) {
  var coercedValue = serializeObject(outputValue);
  if (typeof coercedValue === "string") {
    return coercedValue;
  }
  if (typeof coercedValue === "boolean") {
    return coercedValue ? "true" : "false";
  }
  if (isFinite_default(coercedValue)) {
    return coercedValue.toString();
  }
  throw new GraphQLError("String cannot represent value: ".concat(inspect(outputValue)));
}
function coerceString(inputValue) {
  if (typeof inputValue !== "string") {
    throw new GraphQLError("String cannot represent a non string value: ".concat(inspect(inputValue)));
  }
  return inputValue;
}
var GraphQLString = new GraphQLScalarType({
  name: "String",
  description: "The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.",
  serialize: serializeString,
  parseValue: coerceString,
  parseLiteral: function parseLiteral3(valueNode) {
    if (valueNode.kind !== Kind.STRING) {
      throw new GraphQLError("String cannot represent a non string value: ".concat(print(valueNode)), valueNode);
    }
    return valueNode.value;
  }
});
function serializeBoolean(outputValue) {
  var coercedValue = serializeObject(outputValue);
  if (typeof coercedValue === "boolean") {
    return coercedValue;
  }
  if (isFinite_default(coercedValue)) {
    return coercedValue !== 0;
  }
  throw new GraphQLError("Boolean cannot represent a non boolean value: ".concat(inspect(coercedValue)));
}
function coerceBoolean(inputValue) {
  if (typeof inputValue !== "boolean") {
    throw new GraphQLError("Boolean cannot represent a non boolean value: ".concat(inspect(inputValue)));
  }
  return inputValue;
}
var GraphQLBoolean = new GraphQLScalarType({
  name: "Boolean",
  description: "The `Boolean` scalar type represents `true` or `false`.",
  serialize: serializeBoolean,
  parseValue: coerceBoolean,
  parseLiteral: function parseLiteral4(valueNode) {
    if (valueNode.kind !== Kind.BOOLEAN) {
      throw new GraphQLError("Boolean cannot represent a non boolean value: ".concat(print(valueNode)), valueNode);
    }
    return valueNode.value;
  }
});
function serializeID(outputValue) {
  var coercedValue = serializeObject(outputValue);
  if (typeof coercedValue === "string") {
    return coercedValue;
  }
  if (isInteger_default(coercedValue)) {
    return String(coercedValue);
  }
  throw new GraphQLError("ID cannot represent value: ".concat(inspect(outputValue)));
}
function coerceID(inputValue) {
  if (typeof inputValue === "string") {
    return inputValue;
  }
  if (isInteger_default(inputValue)) {
    return inputValue.toString();
  }
  throw new GraphQLError("ID cannot represent value: ".concat(inspect(inputValue)));
}
var GraphQLID = new GraphQLScalarType({
  name: "ID",
  description: 'The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.',
  serialize: serializeID,
  parseValue: coerceID,
  parseLiteral: function parseLiteral5(valueNode) {
    if (valueNode.kind !== Kind.STRING && valueNode.kind !== Kind.INT) {
      throw new GraphQLError("ID cannot represent a non-string and non-integer value: " + print(valueNode), valueNode);
    }
    return valueNode.value;
  }
});
var specifiedScalarTypes = Object.freeze([GraphQLString, GraphQLInt, GraphQLFloat, GraphQLBoolean, GraphQLID]);

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/astFromValue.mjs
function astFromValue(value, type) {
  if (isNonNullType(type)) {
    var astValue = astFromValue(value, type.ofType);
    if ((astValue === null || astValue === void 0 ? void 0 : astValue.kind) === Kind.NULL) {
      return null;
    }
    return astValue;
  }
  if (value === null) {
    return {
      kind: Kind.NULL
    };
  }
  if (value === void 0) {
    return null;
  }
  if (isListType(type)) {
    var itemType = type.ofType;
    var items = safeArrayFrom(value);
    if (items != null) {
      var valuesNodes = [];
      for (var _i2 = 0; _i2 < items.length; _i2++) {
        var item = items[_i2];
        var itemNode = astFromValue(item, itemType);
        if (itemNode != null) {
          valuesNodes.push(itemNode);
        }
      }
      return {
        kind: Kind.LIST,
        values: valuesNodes
      };
    }
    return astFromValue(value, itemType);
  }
  if (isInputObjectType(type)) {
    if (!isObjectLike(value)) {
      return null;
    }
    var fieldNodes = [];
    for (var _i4 = 0, _objectValues2 = objectValues_default(type.getFields()); _i4 < _objectValues2.length; _i4++) {
      var field = _objectValues2[_i4];
      var fieldValue = astFromValue(value[field.name], field.type);
      if (fieldValue) {
        fieldNodes.push({
          kind: Kind.OBJECT_FIELD,
          name: {
            kind: Kind.NAME,
            value: field.name
          },
          value: fieldValue
        });
      }
    }
    return {
      kind: Kind.OBJECT,
      fields: fieldNodes
    };
  }
  if (isLeafType(type)) {
    var serialized = type.serialize(value);
    if (serialized == null) {
      return null;
    }
    if (typeof serialized === "boolean") {
      return {
        kind: Kind.BOOLEAN,
        value: serialized
      };
    }
    if (typeof serialized === "number" && isFinite_default(serialized)) {
      var stringNum = String(serialized);
      return integerStringRegExp.test(stringNum) ? {
        kind: Kind.INT,
        value: stringNum
      } : {
        kind: Kind.FLOAT,
        value: stringNum
      };
    }
    if (typeof serialized === "string") {
      if (isEnumType(type)) {
        return {
          kind: Kind.ENUM,
          value: serialized
        };
      }
      if (type === GraphQLID && integerStringRegExp.test(serialized)) {
        return {
          kind: Kind.INT,
          value: serialized
        };
      }
      return {
        kind: Kind.STRING,
        value: serialized
      };
    }
    throw new TypeError("Cannot convert value to AST: ".concat(inspect(serialized), "."));
  }
  invariant(0, "Unexpected input type: " + inspect(type));
}
var integerStringRegExp = /^-?(?:0|[1-9][0-9]*)$/;

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/type/introspection.mjs
var __Schema = new GraphQLObjectType({
  name: "__Schema",
  description: "A GraphQL Schema defines the capabilities of a GraphQL server. It exposes all available types and directives on the server, as well as the entry points for query, mutation, and subscription operations.",
  fields: function fields() {
    return {
      description: {
        type: GraphQLString,
        resolve: function resolve4(schema) {
          return schema.description;
        }
      },
      types: {
        description: "A list of all types supported by this server.",
        type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(__Type))),
        resolve: function resolve4(schema) {
          return objectValues_default(schema.getTypeMap());
        }
      },
      queryType: {
        description: "The type that query operations will be rooted at.",
        type: new GraphQLNonNull(__Type),
        resolve: function resolve4(schema) {
          return schema.getQueryType();
        }
      },
      mutationType: {
        description: "If this server supports mutation, the type that mutation operations will be rooted at.",
        type: __Type,
        resolve: function resolve4(schema) {
          return schema.getMutationType();
        }
      },
      subscriptionType: {
        description: "If this server support subscription, the type that subscription operations will be rooted at.",
        type: __Type,
        resolve: function resolve4(schema) {
          return schema.getSubscriptionType();
        }
      },
      directives: {
        description: "A list of all directives supported by this server.",
        type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(__Directive))),
        resolve: function resolve4(schema) {
          return schema.getDirectives();
        }
      }
    };
  }
});
var __Directive = new GraphQLObjectType({
  name: "__Directive",
  description: "A Directive provides a way to describe alternate runtime execution and type validation behavior in a GraphQL document.\n\nIn some cases, you need to provide options to alter GraphQL's execution behavior in ways field arguments will not suffice, such as conditionally including or skipping a field. Directives provide this by describing additional information to the executor.",
  fields: function fields2() {
    return {
      name: {
        type: new GraphQLNonNull(GraphQLString),
        resolve: function resolve4(directive) {
          return directive.name;
        }
      },
      description: {
        type: GraphQLString,
        resolve: function resolve4(directive) {
          return directive.description;
        }
      },
      isRepeatable: {
        type: new GraphQLNonNull(GraphQLBoolean),
        resolve: function resolve4(directive) {
          return directive.isRepeatable;
        }
      },
      locations: {
        type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(__DirectiveLocation))),
        resolve: function resolve4(directive) {
          return directive.locations;
        }
      },
      args: {
        type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(__InputValue))),
        args: {
          includeDeprecated: {
            type: GraphQLBoolean,
            defaultValue: false
          }
        },
        resolve: function resolve4(field, _ref) {
          var includeDeprecated = _ref.includeDeprecated;
          return includeDeprecated ? field.args : field.args.filter(function(arg) {
            return arg.deprecationReason == null;
          });
        }
      }
    };
  }
});
var __DirectiveLocation = new GraphQLEnumType({
  name: "__DirectiveLocation",
  description: "A Directive can be adjacent to many parts of the GraphQL language, a __DirectiveLocation describes one such possible adjacencies.",
  values: {
    QUERY: {
      value: DirectiveLocation.QUERY,
      description: "Location adjacent to a query operation."
    },
    MUTATION: {
      value: DirectiveLocation.MUTATION,
      description: "Location adjacent to a mutation operation."
    },
    SUBSCRIPTION: {
      value: DirectiveLocation.SUBSCRIPTION,
      description: "Location adjacent to a subscription operation."
    },
    FIELD: {
      value: DirectiveLocation.FIELD,
      description: "Location adjacent to a field."
    },
    FRAGMENT_DEFINITION: {
      value: DirectiveLocation.FRAGMENT_DEFINITION,
      description: "Location adjacent to a fragment definition."
    },
    FRAGMENT_SPREAD: {
      value: DirectiveLocation.FRAGMENT_SPREAD,
      description: "Location adjacent to a fragment spread."
    },
    INLINE_FRAGMENT: {
      value: DirectiveLocation.INLINE_FRAGMENT,
      description: "Location adjacent to an inline fragment."
    },
    VARIABLE_DEFINITION: {
      value: DirectiveLocation.VARIABLE_DEFINITION,
      description: "Location adjacent to a variable definition."
    },
    SCHEMA: {
      value: DirectiveLocation.SCHEMA,
      description: "Location adjacent to a schema definition."
    },
    SCALAR: {
      value: DirectiveLocation.SCALAR,
      description: "Location adjacent to a scalar definition."
    },
    OBJECT: {
      value: DirectiveLocation.OBJECT,
      description: "Location adjacent to an object type definition."
    },
    FIELD_DEFINITION: {
      value: DirectiveLocation.FIELD_DEFINITION,
      description: "Location adjacent to a field definition."
    },
    ARGUMENT_DEFINITION: {
      value: DirectiveLocation.ARGUMENT_DEFINITION,
      description: "Location adjacent to an argument definition."
    },
    INTERFACE: {
      value: DirectiveLocation.INTERFACE,
      description: "Location adjacent to an interface definition."
    },
    UNION: {
      value: DirectiveLocation.UNION,
      description: "Location adjacent to a union definition."
    },
    ENUM: {
      value: DirectiveLocation.ENUM,
      description: "Location adjacent to an enum definition."
    },
    ENUM_VALUE: {
      value: DirectiveLocation.ENUM_VALUE,
      description: "Location adjacent to an enum value definition."
    },
    INPUT_OBJECT: {
      value: DirectiveLocation.INPUT_OBJECT,
      description: "Location adjacent to an input object type definition."
    },
    INPUT_FIELD_DEFINITION: {
      value: DirectiveLocation.INPUT_FIELD_DEFINITION,
      description: "Location adjacent to an input object field definition."
    }
  }
});
var __Type = new GraphQLObjectType({
  name: "__Type",
  description: "The fundamental unit of any GraphQL Schema is the type. There are many kinds of types in GraphQL as represented by the `__TypeKind` enum.\n\nDepending on the kind of a type, certain fields describe information about that type. Scalar types provide no information beyond a name, description and optional `specifiedByUrl`, while Enum types provide their values. Object and Interface types provide the fields they describe. Abstract types, Union and Interface, provide the Object types possible at runtime. List and NonNull types compose other types.",
  fields: function fields3() {
    return {
      kind: {
        type: new GraphQLNonNull(__TypeKind),
        resolve: function resolve4(type) {
          if (isScalarType(type)) {
            return TypeKind.SCALAR;
          }
          if (isObjectType(type)) {
            return TypeKind.OBJECT;
          }
          if (isInterfaceType(type)) {
            return TypeKind.INTERFACE;
          }
          if (isUnionType(type)) {
            return TypeKind.UNION;
          }
          if (isEnumType(type)) {
            return TypeKind.ENUM;
          }
          if (isInputObjectType(type)) {
            return TypeKind.INPUT_OBJECT;
          }
          if (isListType(type)) {
            return TypeKind.LIST;
          }
          if (isNonNullType(type)) {
            return TypeKind.NON_NULL;
          }
          invariant(0, 'Unexpected type: "'.concat(inspect(type), '".'));
        }
      },
      name: {
        type: GraphQLString,
        resolve: function resolve4(type) {
          return type.name !== void 0 ? type.name : void 0;
        }
      },
      description: {
        type: GraphQLString,
        resolve: function resolve4(type) {
          return type.description !== void 0 ? type.description : void 0;
        }
      },
      specifiedByUrl: {
        type: GraphQLString,
        resolve: function resolve4(obj) {
          return obj.specifiedByUrl !== void 0 ? obj.specifiedByUrl : void 0;
        }
      },
      fields: {
        type: new GraphQLList(new GraphQLNonNull(__Field)),
        args: {
          includeDeprecated: {
            type: GraphQLBoolean,
            defaultValue: false
          }
        },
        resolve: function resolve4(type, _ref2) {
          var includeDeprecated = _ref2.includeDeprecated;
          if (isObjectType(type) || isInterfaceType(type)) {
            var fields7 = objectValues_default(type.getFields());
            return includeDeprecated ? fields7 : fields7.filter(function(field) {
              return field.deprecationReason == null;
            });
          }
        }
      },
      interfaces: {
        type: new GraphQLList(new GraphQLNonNull(__Type)),
        resolve: function resolve4(type) {
          if (isObjectType(type) || isInterfaceType(type)) {
            return type.getInterfaces();
          }
        }
      },
      possibleTypes: {
        type: new GraphQLList(new GraphQLNonNull(__Type)),
        resolve: function resolve4(type, _args, _context, _ref3) {
          var schema = _ref3.schema;
          if (isAbstractType(type)) {
            return schema.getPossibleTypes(type);
          }
        }
      },
      enumValues: {
        type: new GraphQLList(new GraphQLNonNull(__EnumValue)),
        args: {
          includeDeprecated: {
            type: GraphQLBoolean,
            defaultValue: false
          }
        },
        resolve: function resolve4(type, _ref4) {
          var includeDeprecated = _ref4.includeDeprecated;
          if (isEnumType(type)) {
            var values = type.getValues();
            return includeDeprecated ? values : values.filter(function(field) {
              return field.deprecationReason == null;
            });
          }
        }
      },
      inputFields: {
        type: new GraphQLList(new GraphQLNonNull(__InputValue)),
        args: {
          includeDeprecated: {
            type: GraphQLBoolean,
            defaultValue: false
          }
        },
        resolve: function resolve4(type, _ref5) {
          var includeDeprecated = _ref5.includeDeprecated;
          if (isInputObjectType(type)) {
            var values = objectValues_default(type.getFields());
            return includeDeprecated ? values : values.filter(function(field) {
              return field.deprecationReason == null;
            });
          }
        }
      },
      ofType: {
        type: __Type,
        resolve: function resolve4(type) {
          return type.ofType !== void 0 ? type.ofType : void 0;
        }
      }
    };
  }
});
var __Field = new GraphQLObjectType({
  name: "__Field",
  description: "Object and Interface types are described by a list of Fields, each of which has a name, potentially a list of arguments, and a return type.",
  fields: function fields4() {
    return {
      name: {
        type: new GraphQLNonNull(GraphQLString),
        resolve: function resolve4(field) {
          return field.name;
        }
      },
      description: {
        type: GraphQLString,
        resolve: function resolve4(field) {
          return field.description;
        }
      },
      args: {
        type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(__InputValue))),
        args: {
          includeDeprecated: {
            type: GraphQLBoolean,
            defaultValue: false
          }
        },
        resolve: function resolve4(field, _ref6) {
          var includeDeprecated = _ref6.includeDeprecated;
          return includeDeprecated ? field.args : field.args.filter(function(arg) {
            return arg.deprecationReason == null;
          });
        }
      },
      type: {
        type: new GraphQLNonNull(__Type),
        resolve: function resolve4(field) {
          return field.type;
        }
      },
      isDeprecated: {
        type: new GraphQLNonNull(GraphQLBoolean),
        resolve: function resolve4(field) {
          return field.deprecationReason != null;
        }
      },
      deprecationReason: {
        type: GraphQLString,
        resolve: function resolve4(field) {
          return field.deprecationReason;
        }
      }
    };
  }
});
var __InputValue = new GraphQLObjectType({
  name: "__InputValue",
  description: "Arguments provided to Fields or Directives and the input fields of an InputObject are represented as Input Values which describe their type and optionally a default value.",
  fields: function fields5() {
    return {
      name: {
        type: new GraphQLNonNull(GraphQLString),
        resolve: function resolve4(inputValue) {
          return inputValue.name;
        }
      },
      description: {
        type: GraphQLString,
        resolve: function resolve4(inputValue) {
          return inputValue.description;
        }
      },
      type: {
        type: new GraphQLNonNull(__Type),
        resolve: function resolve4(inputValue) {
          return inputValue.type;
        }
      },
      defaultValue: {
        type: GraphQLString,
        description: "A GraphQL-formatted string representing the default value for this input value.",
        resolve: function resolve4(inputValue) {
          var type = inputValue.type, defaultValue = inputValue.defaultValue;
          var valueAST = astFromValue(defaultValue, type);
          return valueAST ? print(valueAST) : null;
        }
      },
      isDeprecated: {
        type: new GraphQLNonNull(GraphQLBoolean),
        resolve: function resolve4(field) {
          return field.deprecationReason != null;
        }
      },
      deprecationReason: {
        type: GraphQLString,
        resolve: function resolve4(obj) {
          return obj.deprecationReason;
        }
      }
    };
  }
});
var __EnumValue = new GraphQLObjectType({
  name: "__EnumValue",
  description: "One possible value for a given Enum. Enum values are unique values, not a placeholder for a string or numeric value. However an Enum value is returned in a JSON response as a string.",
  fields: function fields6() {
    return {
      name: {
        type: new GraphQLNonNull(GraphQLString),
        resolve: function resolve4(enumValue) {
          return enumValue.name;
        }
      },
      description: {
        type: GraphQLString,
        resolve: function resolve4(enumValue) {
          return enumValue.description;
        }
      },
      isDeprecated: {
        type: new GraphQLNonNull(GraphQLBoolean),
        resolve: function resolve4(enumValue) {
          return enumValue.deprecationReason != null;
        }
      },
      deprecationReason: {
        type: GraphQLString,
        resolve: function resolve4(enumValue) {
          return enumValue.deprecationReason;
        }
      }
    };
  }
});
var TypeKind = Object.freeze({
  SCALAR: "SCALAR",
  OBJECT: "OBJECT",
  INTERFACE: "INTERFACE",
  UNION: "UNION",
  ENUM: "ENUM",
  INPUT_OBJECT: "INPUT_OBJECT",
  LIST: "LIST",
  NON_NULL: "NON_NULL"
});
var __TypeKind = new GraphQLEnumType({
  name: "__TypeKind",
  description: "An enum describing what kind of type a given `__Type` is.",
  values: {
    SCALAR: {
      value: TypeKind.SCALAR,
      description: "Indicates this type is a scalar."
    },
    OBJECT: {
      value: TypeKind.OBJECT,
      description: "Indicates this type is an object. `fields` and `interfaces` are valid fields."
    },
    INTERFACE: {
      value: TypeKind.INTERFACE,
      description: "Indicates this type is an interface. `fields`, `interfaces`, and `possibleTypes` are valid fields."
    },
    UNION: {
      value: TypeKind.UNION,
      description: "Indicates this type is a union. `possibleTypes` is a valid field."
    },
    ENUM: {
      value: TypeKind.ENUM,
      description: "Indicates this type is an enum. `enumValues` is a valid field."
    },
    INPUT_OBJECT: {
      value: TypeKind.INPUT_OBJECT,
      description: "Indicates this type is an input object. `inputFields` is a valid field."
    },
    LIST: {
      value: TypeKind.LIST,
      description: "Indicates this type is a list. `ofType` is a valid field."
    },
    NON_NULL: {
      value: TypeKind.NON_NULL,
      description: "Indicates this type is a non-null. `ofType` is a valid field."
    }
  }
});
var SchemaMetaFieldDef = {
  name: "__schema",
  type: new GraphQLNonNull(__Schema),
  description: "Access the current type schema of this server.",
  args: [],
  resolve: function resolve(_source, _args, _context, _ref7) {
    var schema = _ref7.schema;
    return schema;
  },
  isDeprecated: false,
  deprecationReason: void 0,
  extensions: void 0,
  astNode: void 0
};
var TypeMetaFieldDef = {
  name: "__type",
  type: __Type,
  description: "Request the type information of a single type.",
  args: [{
    name: "name",
    description: void 0,
    type: new GraphQLNonNull(GraphQLString),
    defaultValue: void 0,
    deprecationReason: void 0,
    extensions: void 0,
    astNode: void 0
  }],
  resolve: function resolve2(_source, _ref8, _context, _ref9) {
    var name = _ref8.name;
    var schema = _ref9.schema;
    return schema.getType(name);
  },
  isDeprecated: false,
  deprecationReason: void 0,
  extensions: void 0,
  astNode: void 0
};
var TypeNameMetaFieldDef = {
  name: "__typename",
  type: new GraphQLNonNull(GraphQLString),
  description: "The name of the current Object type at runtime.",
  args: [],
  resolve: function resolve3(_source, _args, _context, _ref10) {
    var parentType = _ref10.parentType;
    return parentType.name;
  },
  isDeprecated: false,
  deprecationReason: void 0,
  extensions: void 0,
  astNode: void 0
};
var introspectionTypes = Object.freeze([__Schema, __Directive, __DirectiveLocation, __Type, __Field, __InputValue, __EnumValue, __TypeKind]);

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/type/directives.mjs
function _defineProperties4(target, props) {
  for (var i = 0; i < props.length; i++) {
    var descriptor = props[i];
    descriptor.enumerable = descriptor.enumerable || false;
    descriptor.configurable = true;
    if ("value" in descriptor) descriptor.writable = true;
    Object.defineProperty(target, descriptor.key, descriptor);
  }
}
function _createClass4(Constructor, protoProps, staticProps) {
  if (protoProps) _defineProperties4(Constructor.prototype, protoProps);
  if (staticProps) _defineProperties4(Constructor, staticProps);
  return Constructor;
}
function isDirective(directive) {
  return instanceOf_default(directive, GraphQLDirective);
}
var GraphQLDirective = function() {
  function GraphQLDirective2(config) {
    var _config$isRepeatable, _config$args;
    this.name = config.name;
    this.description = config.description;
    this.locations = config.locations;
    this.isRepeatable = (_config$isRepeatable = config.isRepeatable) !== null && _config$isRepeatable !== void 0 ? _config$isRepeatable : false;
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    config.name || devAssert(0, "Directive must be named.");
    Array.isArray(config.locations) || devAssert(0, "@".concat(config.name, " locations must be an Array."));
    var args = (_config$args = config.args) !== null && _config$args !== void 0 ? _config$args : {};
    isObjectLike(args) && !Array.isArray(args) || devAssert(0, "@".concat(config.name, " args must be an object with argument names as keys."));
    this.args = objectEntries_default(args).map(function(_ref) {
      var argName = _ref[0], argConfig = _ref[1];
      return {
        name: argName,
        description: argConfig.description,
        type: argConfig.type,
        defaultValue: argConfig.defaultValue,
        deprecationReason: argConfig.deprecationReason,
        extensions: argConfig.extensions && toObjMap(argConfig.extensions),
        astNode: argConfig.astNode
      };
    });
  }
  var _proto = GraphQLDirective2.prototype;
  _proto.toConfig = function toConfig() {
    return {
      name: this.name,
      description: this.description,
      locations: this.locations,
      args: argsToArgsConfig(this.args),
      isRepeatable: this.isRepeatable,
      extensions: this.extensions,
      astNode: this.astNode
    };
  };
  _proto.toString = function toString3() {
    return "@" + this.name;
  };
  _proto.toJSON = function toJSON3() {
    return this.toString();
  };
  _createClass4(GraphQLDirective2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLDirective";
    }
  }]);
  return GraphQLDirective2;
}();
defineInspect(GraphQLDirective);
var GraphQLIncludeDirective = new GraphQLDirective({
  name: "include",
  description: "Directs the executor to include this field or fragment only when the `if` argument is true.",
  locations: [DirectiveLocation.FIELD, DirectiveLocation.FRAGMENT_SPREAD, DirectiveLocation.INLINE_FRAGMENT],
  args: {
    if: {
      type: new GraphQLNonNull(GraphQLBoolean),
      description: "Included when true."
    }
  }
});
var GraphQLSkipDirective = new GraphQLDirective({
  name: "skip",
  description: "Directs the executor to skip this field or fragment when the `if` argument is true.",
  locations: [DirectiveLocation.FIELD, DirectiveLocation.FRAGMENT_SPREAD, DirectiveLocation.INLINE_FRAGMENT],
  args: {
    if: {
      type: new GraphQLNonNull(GraphQLBoolean),
      description: "Skipped when true."
    }
  }
});
var DEFAULT_DEPRECATION_REASON = "No longer supported";
var GraphQLDeprecatedDirective = new GraphQLDirective({
  name: "deprecated",
  description: "Marks an element of a GraphQL schema as no longer supported.",
  locations: [DirectiveLocation.FIELD_DEFINITION, DirectiveLocation.ARGUMENT_DEFINITION, DirectiveLocation.INPUT_FIELD_DEFINITION, DirectiveLocation.ENUM_VALUE],
  args: {
    reason: {
      type: GraphQLString,
      description: "Explains why this element was deprecated, usually also including a suggestion for how to access supported similar data. Formatted using the Markdown syntax, as specified by [CommonMark](https://commonmark.org/).",
      defaultValue: DEFAULT_DEPRECATION_REASON
    }
  }
});
var GraphQLSpecifiedByDirective = new GraphQLDirective({
  name: "specifiedBy",
  description: "Exposes a URL that specifies the behaviour of this scalar.",
  locations: [DirectiveLocation.SCALAR],
  args: {
    url: {
      type: new GraphQLNonNull(GraphQLString),
      description: "The URL that specifies the behaviour of this scalar."
    }
  }
});
var specifiedDirectives = Object.freeze([GraphQLIncludeDirective, GraphQLSkipDirective, GraphQLDeprecatedDirective, GraphQLSpecifiedByDirective]);

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/type/schema.mjs
function _defineProperties5(target, props) {
  for (var i = 0; i < props.length; i++) {
    var descriptor = props[i];
    descriptor.enumerable = descriptor.enumerable || false;
    descriptor.configurable = true;
    if ("value" in descriptor) descriptor.writable = true;
    Object.defineProperty(target, descriptor.key, descriptor);
  }
}
function _createClass5(Constructor, protoProps, staticProps) {
  if (protoProps) _defineProperties5(Constructor.prototype, protoProps);
  if (staticProps) _defineProperties5(Constructor, staticProps);
  return Constructor;
}
var GraphQLSchema = function() {
  function GraphQLSchema2(config) {
    var _config$directives;
    this.__validationErrors = config.assumeValid === true ? [] : void 0;
    isObjectLike(config) || devAssert(0, "Must provide configuration object.");
    !config.types || Array.isArray(config.types) || devAssert(0, '"types" must be Array if provided but got: '.concat(inspect(config.types), "."));
    !config.directives || Array.isArray(config.directives) || devAssert(0, '"directives" must be Array if provided but got: ' + "".concat(inspect(config.directives), "."));
    this.description = config.description;
    this.extensions = config.extensions && toObjMap(config.extensions);
    this.astNode = config.astNode;
    this.extensionASTNodes = config.extensionASTNodes;
    this._queryType = config.query;
    this._mutationType = config.mutation;
    this._subscriptionType = config.subscription;
    this._directives = (_config$directives = config.directives) !== null && _config$directives !== void 0 ? _config$directives : specifiedDirectives;
    var allReferencedTypes = new Set(config.types);
    if (config.types != null) {
      for (var _i2 = 0, _config$types2 = config.types; _i2 < _config$types2.length; _i2++) {
        var type = _config$types2[_i2];
        allReferencedTypes.delete(type);
        collectReferencedTypes(type, allReferencedTypes);
      }
    }
    if (this._queryType != null) {
      collectReferencedTypes(this._queryType, allReferencedTypes);
    }
    if (this._mutationType != null) {
      collectReferencedTypes(this._mutationType, allReferencedTypes);
    }
    if (this._subscriptionType != null) {
      collectReferencedTypes(this._subscriptionType, allReferencedTypes);
    }
    for (var _i4 = 0, _this$_directives2 = this._directives; _i4 < _this$_directives2.length; _i4++) {
      var directive = _this$_directives2[_i4];
      if (isDirective(directive)) {
        for (var _i6 = 0, _directive$args2 = directive.args; _i6 < _directive$args2.length; _i6++) {
          var arg = _directive$args2[_i6];
          collectReferencedTypes(arg.type, allReferencedTypes);
        }
      }
    }
    collectReferencedTypes(__Schema, allReferencedTypes);
    this._typeMap = /* @__PURE__ */ Object.create(null);
    this._subTypeMap = /* @__PURE__ */ Object.create(null);
    this._implementationsMap = /* @__PURE__ */ Object.create(null);
    for (var _i8 = 0, _arrayFrom2 = arrayFrom_default(allReferencedTypes); _i8 < _arrayFrom2.length; _i8++) {
      var namedType = _arrayFrom2[_i8];
      if (namedType == null) {
        continue;
      }
      var typeName = namedType.name;
      typeName || devAssert(0, "One of the provided types for building the Schema is missing a name.");
      if (this._typeMap[typeName] !== void 0) {
        throw new Error('Schema must contain uniquely named types but contains multiple types named "'.concat(typeName, '".'));
      }
      this._typeMap[typeName] = namedType;
      if (isInterfaceType(namedType)) {
        for (var _i10 = 0, _namedType$getInterfa2 = namedType.getInterfaces(); _i10 < _namedType$getInterfa2.length; _i10++) {
          var iface = _namedType$getInterfa2[_i10];
          if (isInterfaceType(iface)) {
            var implementations = this._implementationsMap[iface.name];
            if (implementations === void 0) {
              implementations = this._implementationsMap[iface.name] = {
                objects: [],
                interfaces: []
              };
            }
            implementations.interfaces.push(namedType);
          }
        }
      } else if (isObjectType(namedType)) {
        for (var _i12 = 0, _namedType$getInterfa4 = namedType.getInterfaces(); _i12 < _namedType$getInterfa4.length; _i12++) {
          var _iface = _namedType$getInterfa4[_i12];
          if (isInterfaceType(_iface)) {
            var _implementations = this._implementationsMap[_iface.name];
            if (_implementations === void 0) {
              _implementations = this._implementationsMap[_iface.name] = {
                objects: [],
                interfaces: []
              };
            }
            _implementations.objects.push(namedType);
          }
        }
      }
    }
  }
  var _proto = GraphQLSchema2.prototype;
  _proto.getQueryType = function getQueryType() {
    return this._queryType;
  };
  _proto.getMutationType = function getMutationType() {
    return this._mutationType;
  };
  _proto.getSubscriptionType = function getSubscriptionType() {
    return this._subscriptionType;
  };
  _proto.getTypeMap = function getTypeMap() {
    return this._typeMap;
  };
  _proto.getType = function getType(name) {
    return this.getTypeMap()[name];
  };
  _proto.getPossibleTypes = function getPossibleTypes(abstractType) {
    return isUnionType(abstractType) ? abstractType.getTypes() : this.getImplementations(abstractType).objects;
  };
  _proto.getImplementations = function getImplementations(interfaceType) {
    var implementations = this._implementationsMap[interfaceType.name];
    return implementations !== null && implementations !== void 0 ? implementations : {
      objects: [],
      interfaces: []
    };
  };
  _proto.isPossibleType = function isPossibleType(abstractType, possibleType) {
    return this.isSubType(abstractType, possibleType);
  };
  _proto.isSubType = function isSubType(abstractType, maybeSubType) {
    var map2 = this._subTypeMap[abstractType.name];
    if (map2 === void 0) {
      map2 = /* @__PURE__ */ Object.create(null);
      if (isUnionType(abstractType)) {
        for (var _i14 = 0, _abstractType$getType2 = abstractType.getTypes(); _i14 < _abstractType$getType2.length; _i14++) {
          var type = _abstractType$getType2[_i14];
          map2[type.name] = true;
        }
      } else {
        var implementations = this.getImplementations(abstractType);
        for (var _i16 = 0, _implementations$obje2 = implementations.objects; _i16 < _implementations$obje2.length; _i16++) {
          var _type = _implementations$obje2[_i16];
          map2[_type.name] = true;
        }
        for (var _i18 = 0, _implementations$inte2 = implementations.interfaces; _i18 < _implementations$inte2.length; _i18++) {
          var _type2 = _implementations$inte2[_i18];
          map2[_type2.name] = true;
        }
      }
      this._subTypeMap[abstractType.name] = map2;
    }
    return map2[maybeSubType.name] !== void 0;
  };
  _proto.getDirectives = function getDirectives() {
    return this._directives;
  };
  _proto.getDirective = function getDirective(name) {
    return find_default(this.getDirectives(), function(directive) {
      return directive.name === name;
    });
  };
  _proto.toConfig = function toConfig() {
    var _this$extensionASTNod;
    return {
      description: this.description,
      query: this.getQueryType(),
      mutation: this.getMutationType(),
      subscription: this.getSubscriptionType(),
      types: objectValues_default(this.getTypeMap()),
      directives: this.getDirectives().slice(),
      extensions: this.extensions,
      astNode: this.astNode,
      extensionASTNodes: (_this$extensionASTNod = this.extensionASTNodes) !== null && _this$extensionASTNod !== void 0 ? _this$extensionASTNod : [],
      assumeValid: this.__validationErrors !== void 0
    };
  };
  _createClass5(GraphQLSchema2, [{
    key: SYMBOL_TO_STRING_TAG,
    get: function get5() {
      return "GraphQLSchema";
    }
  }]);
  return GraphQLSchema2;
}();
function collectReferencedTypes(type, typeSet) {
  var namedType = getNamedType(type);
  if (!typeSet.has(namedType)) {
    typeSet.add(namedType);
    if (isUnionType(namedType)) {
      for (var _i20 = 0, _namedType$getTypes2 = namedType.getTypes(); _i20 < _namedType$getTypes2.length; _i20++) {
        var memberType = _namedType$getTypes2[_i20];
        collectReferencedTypes(memberType, typeSet);
      }
    } else if (isObjectType(namedType) || isInterfaceType(namedType)) {
      for (var _i22 = 0, _namedType$getInterfa6 = namedType.getInterfaces(); _i22 < _namedType$getInterfa6.length; _i22++) {
        var interfaceType = _namedType$getInterfa6[_i22];
        collectReferencedTypes(interfaceType, typeSet);
      }
      for (var _i24 = 0, _objectValues2 = objectValues_default(namedType.getFields()); _i24 < _objectValues2.length; _i24++) {
        var field = _objectValues2[_i24];
        collectReferencedTypes(field.type, typeSet);
        for (var _i26 = 0, _field$args2 = field.args; _i26 < _field$args2.length; _i26++) {
          var arg = _field$args2[_i26];
          collectReferencedTypes(arg.type, typeSet);
        }
      }
    } else if (isInputObjectType(namedType)) {
      for (var _i28 = 0, _objectValues4 = objectValues_default(namedType.getFields()); _i28 < _objectValues4.length; _i28++) {
        var _field = _objectValues4[_i28];
        collectReferencedTypes(_field.type, typeSet);
      }
    }
  }
  return typeSet;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/type/validate.mjs
var SchemaValidationContext = function() {
  function SchemaValidationContext2(schema) {
    this._errors = [];
    this.schema = schema;
  }
  var _proto = SchemaValidationContext2.prototype;
  _proto.reportError = function reportError(message, nodes) {
    var _nodes = Array.isArray(nodes) ? nodes.filter(Boolean) : nodes;
    this.addError(new GraphQLError(message, _nodes));
  };
  _proto.addError = function addError(error) {
    this._errors.push(error);
  };
  _proto.getErrors = function getErrors() {
    return this._errors;
  };
  return SchemaValidationContext2;
}();

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/typeFromAST.mjs
function typeFromAST(schema, typeNode) {
  var innerType;
  if (typeNode.kind === Kind.LIST_TYPE) {
    innerType = typeFromAST(schema, typeNode.type);
    return innerType && new GraphQLList(innerType);
  }
  if (typeNode.kind === Kind.NON_NULL_TYPE) {
    innerType = typeFromAST(schema, typeNode.type);
    return innerType && new GraphQLNonNull(innerType);
  }
  if (typeNode.kind === Kind.NAMED_TYPE) {
    return schema.getType(typeNode.name.value);
  }
  invariant(0, "Unexpected type node: " + inspect(typeNode));
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/TypeInfo.mjs
var TypeInfo = function() {
  function TypeInfo2(schema, getFieldDefFn, initialType) {
    this._schema = schema;
    this._typeStack = [];
    this._parentTypeStack = [];
    this._inputTypeStack = [];
    this._fieldDefStack = [];
    this._defaultValueStack = [];
    this._directive = null;
    this._argument = null;
    this._enumValue = null;
    this._getFieldDef = getFieldDefFn !== null && getFieldDefFn !== void 0 ? getFieldDefFn : getFieldDef;
    if (initialType) {
      if (isInputType(initialType)) {
        this._inputTypeStack.push(initialType);
      }
      if (isCompositeType(initialType)) {
        this._parentTypeStack.push(initialType);
      }
      if (isOutputType(initialType)) {
        this._typeStack.push(initialType);
      }
    }
  }
  var _proto = TypeInfo2.prototype;
  _proto.getType = function getType() {
    if (this._typeStack.length > 0) {
      return this._typeStack[this._typeStack.length - 1];
    }
  };
  _proto.getParentType = function getParentType() {
    if (this._parentTypeStack.length > 0) {
      return this._parentTypeStack[this._parentTypeStack.length - 1];
    }
  };
  _proto.getInputType = function getInputType() {
    if (this._inputTypeStack.length > 0) {
      return this._inputTypeStack[this._inputTypeStack.length - 1];
    }
  };
  _proto.getParentInputType = function getParentInputType() {
    if (this._inputTypeStack.length > 1) {
      return this._inputTypeStack[this._inputTypeStack.length - 2];
    }
  };
  _proto.getFieldDef = function getFieldDef3() {
    if (this._fieldDefStack.length > 0) {
      return this._fieldDefStack[this._fieldDefStack.length - 1];
    }
  };
  _proto.getDefaultValue = function getDefaultValue() {
    if (this._defaultValueStack.length > 0) {
      return this._defaultValueStack[this._defaultValueStack.length - 1];
    }
  };
  _proto.getDirective = function getDirective() {
    return this._directive;
  };
  _proto.getArgument = function getArgument() {
    return this._argument;
  };
  _proto.getEnumValue = function getEnumValue() {
    return this._enumValue;
  };
  _proto.enter = function enter(node) {
    var schema = this._schema;
    switch (node.kind) {
      case Kind.SELECTION_SET: {
        var namedType = getNamedType(this.getType());
        this._parentTypeStack.push(isCompositeType(namedType) ? namedType : void 0);
        break;
      }
      case Kind.FIELD: {
        var parentType = this.getParentType();
        var fieldDef;
        var fieldType;
        if (parentType) {
          fieldDef = this._getFieldDef(schema, parentType, node);
          if (fieldDef) {
            fieldType = fieldDef.type;
          }
        }
        this._fieldDefStack.push(fieldDef);
        this._typeStack.push(isOutputType(fieldType) ? fieldType : void 0);
        break;
      }
      case Kind.DIRECTIVE:
        this._directive = schema.getDirective(node.name.value);
        break;
      case Kind.OPERATION_DEFINITION: {
        var type;
        switch (node.operation) {
          case "query":
            type = schema.getQueryType();
            break;
          case "mutation":
            type = schema.getMutationType();
            break;
          case "subscription":
            type = schema.getSubscriptionType();
            break;
        }
        this._typeStack.push(isObjectType(type) ? type : void 0);
        break;
      }
      case Kind.INLINE_FRAGMENT:
      case Kind.FRAGMENT_DEFINITION: {
        var typeConditionAST = node.typeCondition;
        var outputType = typeConditionAST ? typeFromAST(schema, typeConditionAST) : getNamedType(this.getType());
        this._typeStack.push(isOutputType(outputType) ? outputType : void 0);
        break;
      }
      case Kind.VARIABLE_DEFINITION: {
        var inputType = typeFromAST(schema, node.type);
        this._inputTypeStack.push(isInputType(inputType) ? inputType : void 0);
        break;
      }
      case Kind.ARGUMENT: {
        var _this$getDirective;
        var argDef;
        var argType;
        var fieldOrDirective = (_this$getDirective = this.getDirective()) !== null && _this$getDirective !== void 0 ? _this$getDirective : this.getFieldDef();
        if (fieldOrDirective) {
          argDef = find_default(fieldOrDirective.args, function(arg) {
            return arg.name === node.name.value;
          });
          if (argDef) {
            argType = argDef.type;
          }
        }
        this._argument = argDef;
        this._defaultValueStack.push(argDef ? argDef.defaultValue : void 0);
        this._inputTypeStack.push(isInputType(argType) ? argType : void 0);
        break;
      }
      case Kind.LIST: {
        var listType = getNullableType(this.getInputType());
        var itemType = isListType(listType) ? listType.ofType : listType;
        this._defaultValueStack.push(void 0);
        this._inputTypeStack.push(isInputType(itemType) ? itemType : void 0);
        break;
      }
      case Kind.OBJECT_FIELD: {
        var objectType = getNamedType(this.getInputType());
        var inputFieldType;
        var inputField;
        if (isInputObjectType(objectType)) {
          inputField = objectType.getFields()[node.name.value];
          if (inputField) {
            inputFieldType = inputField.type;
          }
        }
        this._defaultValueStack.push(inputField ? inputField.defaultValue : void 0);
        this._inputTypeStack.push(isInputType(inputFieldType) ? inputFieldType : void 0);
        break;
      }
      case Kind.ENUM: {
        var enumType = getNamedType(this.getInputType());
        var enumValue;
        if (isEnumType(enumType)) {
          enumValue = enumType.getValue(node.value);
        }
        this._enumValue = enumValue;
        break;
      }
    }
  };
  _proto.leave = function leave(node) {
    switch (node.kind) {
      case Kind.SELECTION_SET:
        this._parentTypeStack.pop();
        break;
      case Kind.FIELD:
        this._fieldDefStack.pop();
        this._typeStack.pop();
        break;
      case Kind.DIRECTIVE:
        this._directive = null;
        break;
      case Kind.OPERATION_DEFINITION:
      case Kind.INLINE_FRAGMENT:
      case Kind.FRAGMENT_DEFINITION:
        this._typeStack.pop();
        break;
      case Kind.VARIABLE_DEFINITION:
        this._inputTypeStack.pop();
        break;
      case Kind.ARGUMENT:
        this._argument = null;
        this._defaultValueStack.pop();
        this._inputTypeStack.pop();
        break;
      case Kind.LIST:
      case Kind.OBJECT_FIELD:
        this._defaultValueStack.pop();
        this._inputTypeStack.pop();
        break;
      case Kind.ENUM:
        this._enumValue = null;
        break;
    }
  };
  return TypeInfo2;
}();
function getFieldDef(schema, parentType, fieldNode) {
  var name = fieldNode.name.value;
  if (name === SchemaMetaFieldDef.name && schema.getQueryType() === parentType) {
    return SchemaMetaFieldDef;
  }
  if (name === TypeMetaFieldDef.name && schema.getQueryType() === parentType) {
    return TypeMetaFieldDef;
  }
  if (name === TypeNameMetaFieldDef.name && isCompositeType(parentType)) {
    return TypeNameMetaFieldDef;
  }
  if (isObjectType(parentType) || isInterfaceType(parentType)) {
    return parentType.getFields()[name];
  }
}
function visitWithTypeInfo(typeInfo, visitor) {
  return {
    enter: function enter(node) {
      typeInfo.enter(node);
      var fn = getVisitFn(
        visitor,
        node.kind,
        /* isLeaving */
        false
      );
      if (fn) {
        var result = fn.apply(visitor, arguments);
        if (result !== void 0) {
          typeInfo.leave(node);
          if (isNode(result)) {
            typeInfo.enter(result);
          }
        }
        return result;
      }
    },
    leave: function leave(node) {
      var fn = getVisitFn(
        visitor,
        node.kind,
        /* isLeaving */
        true
      );
      var result;
      if (fn) {
        result = fn.apply(visitor, arguments);
      }
      typeInfo.leave(node);
      return result;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/language/predicates.mjs
function isExecutableDefinitionNode(node) {
  return node.kind === Kind.OPERATION_DEFINITION || node.kind === Kind.FRAGMENT_DEFINITION;
}
function isTypeSystemDefinitionNode(node) {
  return node.kind === Kind.SCHEMA_DEFINITION || isTypeDefinitionNode(node) || node.kind === Kind.DIRECTIVE_DEFINITION;
}
function isTypeDefinitionNode(node) {
  return node.kind === Kind.SCALAR_TYPE_DEFINITION || node.kind === Kind.OBJECT_TYPE_DEFINITION || node.kind === Kind.INTERFACE_TYPE_DEFINITION || node.kind === Kind.UNION_TYPE_DEFINITION || node.kind === Kind.ENUM_TYPE_DEFINITION || node.kind === Kind.INPUT_OBJECT_TYPE_DEFINITION;
}
function isTypeSystemExtensionNode(node) {
  return node.kind === Kind.SCHEMA_EXTENSION || isTypeExtensionNode(node);
}
function isTypeExtensionNode(node) {
  return node.kind === Kind.SCALAR_TYPE_EXTENSION || node.kind === Kind.OBJECT_TYPE_EXTENSION || node.kind === Kind.INTERFACE_TYPE_EXTENSION || node.kind === Kind.UNION_TYPE_EXTENSION || node.kind === Kind.ENUM_TYPE_EXTENSION || node.kind === Kind.INPUT_OBJECT_TYPE_EXTENSION;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/ExecutableDefinitionsRule.mjs
function ExecutableDefinitionsRule(context) {
  return {
    Document: function Document2(node) {
      for (var _i2 = 0, _node$definitions2 = node.definitions; _i2 < _node$definitions2.length; _i2++) {
        var definition = _node$definitions2[_i2];
        if (!isExecutableDefinitionNode(definition)) {
          var defName = definition.kind === Kind.SCHEMA_DEFINITION || definition.kind === Kind.SCHEMA_EXTENSION ? "schema" : '"' + definition.name.value + '"';
          context.reportError(new GraphQLError("The ".concat(defName, " definition is not executable."), definition));
        }
      }
      return false;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueOperationNamesRule.mjs
function UniqueOperationNamesRule(context) {
  var knownOperationNames = /* @__PURE__ */ Object.create(null);
  return {
    OperationDefinition: function OperationDefinition2(node) {
      var operationName = node.name;
      if (operationName) {
        if (knownOperationNames[operationName.value]) {
          context.reportError(new GraphQLError('There can be only one operation named "'.concat(operationName.value, '".'), [knownOperationNames[operationName.value], operationName]));
        } else {
          knownOperationNames[operationName.value] = operationName;
        }
      }
      return false;
    },
    FragmentDefinition: function FragmentDefinition2() {
      return false;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/LoneAnonymousOperationRule.mjs
function LoneAnonymousOperationRule(context) {
  var operationCount = 0;
  return {
    Document: function Document2(node) {
      operationCount = node.definitions.filter(function(definition) {
        return definition.kind === Kind.OPERATION_DEFINITION;
      }).length;
    },
    OperationDefinition: function OperationDefinition2(node) {
      if (!node.name && operationCount > 1) {
        context.reportError(new GraphQLError("This anonymous operation must be the only defined operation.", node));
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/SingleFieldSubscriptionsRule.mjs
function SingleFieldSubscriptionsRule(context) {
  return {
    OperationDefinition: function OperationDefinition2(node) {
      if (node.operation === "subscription") {
        if (node.selectionSet.selections.length !== 1) {
          context.reportError(new GraphQLError(node.name ? 'Subscription "'.concat(node.name.value, '" must select only one top level field.') : "Anonymous Subscription must select only one top level field.", node.selectionSet.selections.slice(1)));
        }
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/KnownTypeNamesRule.mjs
function KnownTypeNamesRule(context) {
  var schema = context.getSchema();
  var existingTypesMap = schema ? schema.getTypeMap() : /* @__PURE__ */ Object.create(null);
  var definedTypes = /* @__PURE__ */ Object.create(null);
  for (var _i2 = 0, _context$getDocument$2 = context.getDocument().definitions; _i2 < _context$getDocument$2.length; _i2++) {
    var def = _context$getDocument$2[_i2];
    if (isTypeDefinitionNode(def)) {
      definedTypes[def.name.value] = true;
    }
  }
  var typeNames = Object.keys(existingTypesMap).concat(Object.keys(definedTypes));
  return {
    NamedType: function NamedType2(node, _1, parent, _2, ancestors) {
      var typeName = node.name.value;
      if (!existingTypesMap[typeName] && !definedTypes[typeName]) {
        var _ancestors$;
        var definitionNode = (_ancestors$ = ancestors[2]) !== null && _ancestors$ !== void 0 ? _ancestors$ : parent;
        var isSDL = definitionNode != null && isSDLNode(definitionNode);
        if (isSDL && isStandardTypeName(typeName)) {
          return;
        }
        var suggestedTypes = suggestionList(typeName, isSDL ? standardTypeNames.concat(typeNames) : typeNames);
        context.reportError(new GraphQLError('Unknown type "'.concat(typeName, '".') + didYouMean(suggestedTypes), node));
      }
    }
  };
}
var standardTypeNames = [].concat(specifiedScalarTypes, introspectionTypes).map(function(type) {
  return type.name;
});
function isStandardTypeName(typeName) {
  return standardTypeNames.indexOf(typeName) !== -1;
}
function isSDLNode(value) {
  return !Array.isArray(value) && (isTypeSystemDefinitionNode(value) || isTypeSystemExtensionNode(value));
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/FragmentsOnCompositeTypesRule.mjs
function FragmentsOnCompositeTypesRule(context) {
  return {
    InlineFragment: function InlineFragment2(node) {
      var typeCondition = node.typeCondition;
      if (typeCondition) {
        var type = typeFromAST(context.getSchema(), typeCondition);
        if (type && !isCompositeType(type)) {
          var typeStr = print(typeCondition);
          context.reportError(new GraphQLError('Fragment cannot condition on non composite type "'.concat(typeStr, '".'), typeCondition));
        }
      }
    },
    FragmentDefinition: function FragmentDefinition2(node) {
      var type = typeFromAST(context.getSchema(), node.typeCondition);
      if (type && !isCompositeType(type)) {
        var typeStr = print(node.typeCondition);
        context.reportError(new GraphQLError('Fragment "'.concat(node.name.value, '" cannot condition on non composite type "').concat(typeStr, '".'), node.typeCondition));
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/VariablesAreInputTypesRule.mjs
function VariablesAreInputTypesRule(context) {
  return {
    VariableDefinition: function VariableDefinition2(node) {
      var type = typeFromAST(context.getSchema(), node.type);
      if (type && !isInputType(type)) {
        var variableName = node.variable.name.value;
        var typeName = print(node.type);
        context.reportError(new GraphQLError('Variable "$'.concat(variableName, '" cannot be non-input type "').concat(typeName, '".'), node.type));
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/ScalarLeafsRule.mjs
function ScalarLeafsRule(context) {
  return {
    Field: function Field2(node) {
      var type = context.getType();
      var selectionSet = node.selectionSet;
      if (type) {
        if (isLeafType(getNamedType(type))) {
          if (selectionSet) {
            var fieldName = node.name.value;
            var typeStr = inspect(type);
            context.reportError(new GraphQLError('Field "'.concat(fieldName, '" must not have a selection since type "').concat(typeStr, '" has no subfields.'), selectionSet));
          }
        } else if (!selectionSet) {
          var _fieldName = node.name.value;
          var _typeStr = inspect(type);
          context.reportError(new GraphQLError('Field "'.concat(_fieldName, '" of type "').concat(_typeStr, '" must have a selection of subfields. Did you mean "').concat(_fieldName, ' { ... }"?'), node));
        }
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/FieldsOnCorrectTypeRule.mjs
function FieldsOnCorrectTypeRule(context) {
  return {
    Field: function Field2(node) {
      var type = context.getParentType();
      if (type) {
        var fieldDef = context.getFieldDef();
        if (!fieldDef) {
          var schema = context.getSchema();
          var fieldName = node.name.value;
          var suggestion = didYouMean("to use an inline fragment on", getSuggestedTypeNames(schema, type, fieldName));
          if (suggestion === "") {
            suggestion = didYouMean(getSuggestedFieldNames(type, fieldName));
          }
          context.reportError(new GraphQLError('Cannot query field "'.concat(fieldName, '" on type "').concat(type.name, '".') + suggestion, node));
        }
      }
    }
  };
}
function getSuggestedTypeNames(schema, type, fieldName) {
  if (!isAbstractType(type)) {
    return [];
  }
  var suggestedTypes = /* @__PURE__ */ new Set();
  var usageCount = /* @__PURE__ */ Object.create(null);
  for (var _i2 = 0, _schema$getPossibleTy2 = schema.getPossibleTypes(type); _i2 < _schema$getPossibleTy2.length; _i2++) {
    var possibleType = _schema$getPossibleTy2[_i2];
    if (!possibleType.getFields()[fieldName]) {
      continue;
    }
    suggestedTypes.add(possibleType);
    usageCount[possibleType.name] = 1;
    for (var _i4 = 0, _possibleType$getInte2 = possibleType.getInterfaces(); _i4 < _possibleType$getInte2.length; _i4++) {
      var _usageCount$possibleI;
      var possibleInterface = _possibleType$getInte2[_i4];
      if (!possibleInterface.getFields()[fieldName]) {
        continue;
      }
      suggestedTypes.add(possibleInterface);
      usageCount[possibleInterface.name] = ((_usageCount$possibleI = usageCount[possibleInterface.name]) !== null && _usageCount$possibleI !== void 0 ? _usageCount$possibleI : 0) + 1;
    }
  }
  return arrayFrom_default(suggestedTypes).sort(function(typeA, typeB) {
    var usageCountDiff = usageCount[typeB.name] - usageCount[typeA.name];
    if (usageCountDiff !== 0) {
      return usageCountDiff;
    }
    if (isInterfaceType(typeA) && schema.isSubType(typeA, typeB)) {
      return -1;
    }
    if (isInterfaceType(typeB) && schema.isSubType(typeB, typeA)) {
      return 1;
    }
    return naturalCompare(typeA.name, typeB.name);
  }).map(function(x) {
    return x.name;
  });
}
function getSuggestedFieldNames(type, fieldName) {
  if (isObjectType(type) || isInterfaceType(type)) {
    var possibleFieldNames = Object.keys(type.getFields());
    return suggestionList(fieldName, possibleFieldNames);
  }
  return [];
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueFragmentNamesRule.mjs
function UniqueFragmentNamesRule(context) {
  var knownFragmentNames = /* @__PURE__ */ Object.create(null);
  return {
    OperationDefinition: function OperationDefinition2() {
      return false;
    },
    FragmentDefinition: function FragmentDefinition2(node) {
      var fragmentName = node.name.value;
      if (knownFragmentNames[fragmentName]) {
        context.reportError(new GraphQLError('There can be only one fragment named "'.concat(fragmentName, '".'), [knownFragmentNames[fragmentName], node.name]));
      } else {
        knownFragmentNames[fragmentName] = node.name;
      }
      return false;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/KnownFragmentNamesRule.mjs
function KnownFragmentNamesRule(context) {
  return {
    FragmentSpread: function FragmentSpread2(node) {
      var fragmentName = node.name.value;
      var fragment = context.getFragment(fragmentName);
      if (!fragment) {
        context.reportError(new GraphQLError('Unknown fragment "'.concat(fragmentName, '".'), node.name));
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/NoUnusedFragmentsRule.mjs
function NoUnusedFragmentsRule(context) {
  var operationDefs = [];
  var fragmentDefs = [];
  return {
    OperationDefinition: function OperationDefinition2(node) {
      operationDefs.push(node);
      return false;
    },
    FragmentDefinition: function FragmentDefinition2(node) {
      fragmentDefs.push(node);
      return false;
    },
    Document: {
      leave: function leave() {
        var fragmentNameUsed = /* @__PURE__ */ Object.create(null);
        for (var _i2 = 0; _i2 < operationDefs.length; _i2++) {
          var operation = operationDefs[_i2];
          for (var _i4 = 0, _context$getRecursive2 = context.getRecursivelyReferencedFragments(operation); _i4 < _context$getRecursive2.length; _i4++) {
            var fragment = _context$getRecursive2[_i4];
            fragmentNameUsed[fragment.name.value] = true;
          }
        }
        for (var _i6 = 0; _i6 < fragmentDefs.length; _i6++) {
          var fragmentDef = fragmentDefs[_i6];
          var fragName = fragmentDef.name.value;
          if (fragmentNameUsed[fragName] !== true) {
            context.reportError(new GraphQLError('Fragment "'.concat(fragName, '" is never used.'), fragmentDef));
          }
        }
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/PossibleFragmentSpreadsRule.mjs
function PossibleFragmentSpreadsRule(context) {
  return {
    InlineFragment: function InlineFragment2(node) {
      var fragType = context.getType();
      var parentType = context.getParentType();
      if (isCompositeType(fragType) && isCompositeType(parentType) && !doTypesOverlap(context.getSchema(), fragType, parentType)) {
        var parentTypeStr = inspect(parentType);
        var fragTypeStr = inspect(fragType);
        context.reportError(new GraphQLError('Fragment cannot be spread here as objects of type "'.concat(parentTypeStr, '" can never be of type "').concat(fragTypeStr, '".'), node));
      }
    },
    FragmentSpread: function FragmentSpread2(node) {
      var fragName = node.name.value;
      var fragType = getFragmentType(context, fragName);
      var parentType = context.getParentType();
      if (fragType && parentType && !doTypesOverlap(context.getSchema(), fragType, parentType)) {
        var parentTypeStr = inspect(parentType);
        var fragTypeStr = inspect(fragType);
        context.reportError(new GraphQLError('Fragment "'.concat(fragName, '" cannot be spread here as objects of type "').concat(parentTypeStr, '" can never be of type "').concat(fragTypeStr, '".'), node));
      }
    }
  };
}
function getFragmentType(context, name) {
  var frag = context.getFragment(name);
  if (frag) {
    var type = typeFromAST(context.getSchema(), frag.typeCondition);
    if (isCompositeType(type)) {
      return type;
    }
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/NoFragmentCyclesRule.mjs
function NoFragmentCyclesRule(context) {
  var visitedFrags = /* @__PURE__ */ Object.create(null);
  var spreadPath = [];
  var spreadPathIndexByName = /* @__PURE__ */ Object.create(null);
  return {
    OperationDefinition: function OperationDefinition2() {
      return false;
    },
    FragmentDefinition: function FragmentDefinition2(node) {
      detectCycleRecursive(node);
      return false;
    }
  };
  function detectCycleRecursive(fragment) {
    if (visitedFrags[fragment.name.value]) {
      return;
    }
    var fragmentName = fragment.name.value;
    visitedFrags[fragmentName] = true;
    var spreadNodes = context.getFragmentSpreads(fragment.selectionSet);
    if (spreadNodes.length === 0) {
      return;
    }
    spreadPathIndexByName[fragmentName] = spreadPath.length;
    for (var _i2 = 0; _i2 < spreadNodes.length; _i2++) {
      var spreadNode = spreadNodes[_i2];
      var spreadName = spreadNode.name.value;
      var cycleIndex = spreadPathIndexByName[spreadName];
      spreadPath.push(spreadNode);
      if (cycleIndex === void 0) {
        var spreadFragment = context.getFragment(spreadName);
        if (spreadFragment) {
          detectCycleRecursive(spreadFragment);
        }
      } else {
        var cyclePath = spreadPath.slice(cycleIndex);
        var viaPath = cyclePath.slice(0, -1).map(function(s) {
          return '"' + s.name.value + '"';
        }).join(", ");
        context.reportError(new GraphQLError('Cannot spread fragment "'.concat(spreadName, '" within itself') + (viaPath !== "" ? " via ".concat(viaPath, ".") : "."), cyclePath));
      }
      spreadPath.pop();
    }
    spreadPathIndexByName[fragmentName] = void 0;
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueVariableNamesRule.mjs
function UniqueVariableNamesRule(context) {
  var knownVariableNames = /* @__PURE__ */ Object.create(null);
  return {
    OperationDefinition: function OperationDefinition2() {
      knownVariableNames = /* @__PURE__ */ Object.create(null);
    },
    VariableDefinition: function VariableDefinition2(node) {
      var variableName = node.variable.name.value;
      if (knownVariableNames[variableName]) {
        context.reportError(new GraphQLError('There can be only one variable named "$'.concat(variableName, '".'), [knownVariableNames[variableName], node.variable.name]));
      } else {
        knownVariableNames[variableName] = node.variable.name;
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/NoUndefinedVariablesRule.mjs
function NoUndefinedVariablesRule(context) {
  var variableNameDefined = /* @__PURE__ */ Object.create(null);
  return {
    OperationDefinition: {
      enter: function enter() {
        variableNameDefined = /* @__PURE__ */ Object.create(null);
      },
      leave: function leave(operation) {
        var usages = context.getRecursiveVariableUsages(operation);
        for (var _i2 = 0; _i2 < usages.length; _i2++) {
          var _ref2 = usages[_i2];
          var node = _ref2.node;
          var varName = node.name.value;
          if (variableNameDefined[varName] !== true) {
            context.reportError(new GraphQLError(operation.name ? 'Variable "$'.concat(varName, '" is not defined by operation "').concat(operation.name.value, '".') : 'Variable "$'.concat(varName, '" is not defined.'), [node, operation]));
          }
        }
      }
    },
    VariableDefinition: function VariableDefinition2(node) {
      variableNameDefined[node.variable.name.value] = true;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/NoUnusedVariablesRule.mjs
function NoUnusedVariablesRule(context) {
  var variableDefs = [];
  return {
    OperationDefinition: {
      enter: function enter() {
        variableDefs = [];
      },
      leave: function leave(operation) {
        var variableNameUsed = /* @__PURE__ */ Object.create(null);
        var usages = context.getRecursiveVariableUsages(operation);
        for (var _i2 = 0; _i2 < usages.length; _i2++) {
          var _ref2 = usages[_i2];
          var node = _ref2.node;
          variableNameUsed[node.name.value] = true;
        }
        for (var _i4 = 0, _variableDefs2 = variableDefs; _i4 < _variableDefs2.length; _i4++) {
          var variableDef = _variableDefs2[_i4];
          var variableName = variableDef.variable.name.value;
          if (variableNameUsed[variableName] !== true) {
            context.reportError(new GraphQLError(operation.name ? 'Variable "$'.concat(variableName, '" is never used in operation "').concat(operation.name.value, '".') : 'Variable "$'.concat(variableName, '" is never used.'), variableDef));
          }
        }
      }
    },
    VariableDefinition: function VariableDefinition2(def) {
      variableDefs.push(def);
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/KnownDirectivesRule.mjs
function KnownDirectivesRule(context) {
  var locationsMap = /* @__PURE__ */ Object.create(null);
  var schema = context.getSchema();
  var definedDirectives = schema ? schema.getDirectives() : specifiedDirectives;
  for (var _i2 = 0; _i2 < definedDirectives.length; _i2++) {
    var directive = definedDirectives[_i2];
    locationsMap[directive.name] = directive.locations;
  }
  var astDefinitions = context.getDocument().definitions;
  for (var _i4 = 0; _i4 < astDefinitions.length; _i4++) {
    var def = astDefinitions[_i4];
    if (def.kind === Kind.DIRECTIVE_DEFINITION) {
      locationsMap[def.name.value] = def.locations.map(function(name) {
        return name.value;
      });
    }
  }
  return {
    Directive: function Directive2(node, _key, _parent, _path, ancestors) {
      var name = node.name.value;
      var locations = locationsMap[name];
      if (!locations) {
        context.reportError(new GraphQLError('Unknown directive "@'.concat(name, '".'), node));
        return;
      }
      var candidateLocation = getDirectiveLocationForASTPath(ancestors);
      if (candidateLocation && locations.indexOf(candidateLocation) === -1) {
        context.reportError(new GraphQLError('Directive "@'.concat(name, '" may not be used on ').concat(candidateLocation, "."), node));
      }
    }
  };
}
function getDirectiveLocationForASTPath(ancestors) {
  var appliedTo = ancestors[ancestors.length - 1];
  !Array.isArray(appliedTo) || invariant(0);
  switch (appliedTo.kind) {
    case Kind.OPERATION_DEFINITION:
      return getDirectiveLocationForOperation(appliedTo.operation);
    case Kind.FIELD:
      return DirectiveLocation.FIELD;
    case Kind.FRAGMENT_SPREAD:
      return DirectiveLocation.FRAGMENT_SPREAD;
    case Kind.INLINE_FRAGMENT:
      return DirectiveLocation.INLINE_FRAGMENT;
    case Kind.FRAGMENT_DEFINITION:
      return DirectiveLocation.FRAGMENT_DEFINITION;
    case Kind.VARIABLE_DEFINITION:
      return DirectiveLocation.VARIABLE_DEFINITION;
    case Kind.SCHEMA_DEFINITION:
    case Kind.SCHEMA_EXTENSION:
      return DirectiveLocation.SCHEMA;
    case Kind.SCALAR_TYPE_DEFINITION:
    case Kind.SCALAR_TYPE_EXTENSION:
      return DirectiveLocation.SCALAR;
    case Kind.OBJECT_TYPE_DEFINITION:
    case Kind.OBJECT_TYPE_EXTENSION:
      return DirectiveLocation.OBJECT;
    case Kind.FIELD_DEFINITION:
      return DirectiveLocation.FIELD_DEFINITION;
    case Kind.INTERFACE_TYPE_DEFINITION:
    case Kind.INTERFACE_TYPE_EXTENSION:
      return DirectiveLocation.INTERFACE;
    case Kind.UNION_TYPE_DEFINITION:
    case Kind.UNION_TYPE_EXTENSION:
      return DirectiveLocation.UNION;
    case Kind.ENUM_TYPE_DEFINITION:
    case Kind.ENUM_TYPE_EXTENSION:
      return DirectiveLocation.ENUM;
    case Kind.ENUM_VALUE_DEFINITION:
      return DirectiveLocation.ENUM_VALUE;
    case Kind.INPUT_OBJECT_TYPE_DEFINITION:
    case Kind.INPUT_OBJECT_TYPE_EXTENSION:
      return DirectiveLocation.INPUT_OBJECT;
    case Kind.INPUT_VALUE_DEFINITION: {
      var parentNode = ancestors[ancestors.length - 3];
      return parentNode.kind === Kind.INPUT_OBJECT_TYPE_DEFINITION ? DirectiveLocation.INPUT_FIELD_DEFINITION : DirectiveLocation.ARGUMENT_DEFINITION;
    }
  }
}
function getDirectiveLocationForOperation(operation) {
  switch (operation) {
    case "query":
      return DirectiveLocation.QUERY;
    case "mutation":
      return DirectiveLocation.MUTATION;
    case "subscription":
      return DirectiveLocation.SUBSCRIPTION;
  }
  invariant(0, "Unexpected operation: " + inspect(operation));
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueDirectivesPerLocationRule.mjs
function UniqueDirectivesPerLocationRule(context) {
  var uniqueDirectiveMap = /* @__PURE__ */ Object.create(null);
  var schema = context.getSchema();
  var definedDirectives = schema ? schema.getDirectives() : specifiedDirectives;
  for (var _i2 = 0; _i2 < definedDirectives.length; _i2++) {
    var directive = definedDirectives[_i2];
    uniqueDirectiveMap[directive.name] = !directive.isRepeatable;
  }
  var astDefinitions = context.getDocument().definitions;
  for (var _i4 = 0; _i4 < astDefinitions.length; _i4++) {
    var def = astDefinitions[_i4];
    if (def.kind === Kind.DIRECTIVE_DEFINITION) {
      uniqueDirectiveMap[def.name.value] = !def.repeatable;
    }
  }
  var schemaDirectives = /* @__PURE__ */ Object.create(null);
  var typeDirectivesMap = /* @__PURE__ */ Object.create(null);
  return {
    // Many different AST nodes may contain directives. Rather than listing
    // them all, just listen for entering any node, and check to see if it
    // defines any directives.
    enter: function enter(node) {
      if (node.directives == null) {
        return;
      }
      var seenDirectives;
      if (node.kind === Kind.SCHEMA_DEFINITION || node.kind === Kind.SCHEMA_EXTENSION) {
        seenDirectives = schemaDirectives;
      } else if (isTypeDefinitionNode(node) || isTypeExtensionNode(node)) {
        var typeName = node.name.value;
        seenDirectives = typeDirectivesMap[typeName];
        if (seenDirectives === void 0) {
          typeDirectivesMap[typeName] = seenDirectives = /* @__PURE__ */ Object.create(null);
        }
      } else {
        seenDirectives = /* @__PURE__ */ Object.create(null);
      }
      for (var _i6 = 0, _node$directives2 = node.directives; _i6 < _node$directives2.length; _i6++) {
        var _directive = _node$directives2[_i6];
        var directiveName = _directive.name.value;
        if (uniqueDirectiveMap[directiveName]) {
          if (seenDirectives[directiveName]) {
            context.reportError(new GraphQLError('The directive "@'.concat(directiveName, '" can only be used once at this location.'), [seenDirectives[directiveName], _directive]));
          } else {
            seenDirectives[directiveName] = _directive;
          }
        }
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/KnownArgumentNamesRule.mjs
function ownKeys2(object, enumerableOnly) {
  var keys = Object.keys(object);
  if (Object.getOwnPropertySymbols) {
    var symbols = Object.getOwnPropertySymbols(object);
    if (enumerableOnly) symbols = symbols.filter(function(sym) {
      return Object.getOwnPropertyDescriptor(object, sym).enumerable;
    });
    keys.push.apply(keys, symbols);
  }
  return keys;
}
function _objectSpread2(target) {
  for (var i = 1; i < arguments.length; i++) {
    var source = arguments[i] != null ? arguments[i] : {};
    if (i % 2) {
      ownKeys2(Object(source), true).forEach(function(key) {
        _defineProperty2(target, key, source[key]);
      });
    } else if (Object.getOwnPropertyDescriptors) {
      Object.defineProperties(target, Object.getOwnPropertyDescriptors(source));
    } else {
      ownKeys2(Object(source)).forEach(function(key) {
        Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
      });
    }
  }
  return target;
}
function _defineProperty2(obj, key, value) {
  if (key in obj) {
    Object.defineProperty(obj, key, { value, enumerable: true, configurable: true, writable: true });
  } else {
    obj[key] = value;
  }
  return obj;
}
function KnownArgumentNamesRule(context) {
  return _objectSpread2(_objectSpread2({}, KnownArgumentNamesOnDirectivesRule(context)), {}, {
    Argument: function Argument2(argNode) {
      var argDef = context.getArgument();
      var fieldDef = context.getFieldDef();
      var parentType = context.getParentType();
      if (!argDef && fieldDef && parentType) {
        var argName = argNode.name.value;
        var knownArgsNames = fieldDef.args.map(function(arg) {
          return arg.name;
        });
        var suggestions = suggestionList(argName, knownArgsNames);
        context.reportError(new GraphQLError('Unknown argument "'.concat(argName, '" on field "').concat(parentType.name, ".").concat(fieldDef.name, '".') + didYouMean(suggestions), argNode));
      }
    }
  });
}
function KnownArgumentNamesOnDirectivesRule(context) {
  var directiveArgs = /* @__PURE__ */ Object.create(null);
  var schema = context.getSchema();
  var definedDirectives = schema ? schema.getDirectives() : specifiedDirectives;
  for (var _i2 = 0; _i2 < definedDirectives.length; _i2++) {
    var directive = definedDirectives[_i2];
    directiveArgs[directive.name] = directive.args.map(function(arg) {
      return arg.name;
    });
  }
  var astDefinitions = context.getDocument().definitions;
  for (var _i4 = 0; _i4 < astDefinitions.length; _i4++) {
    var def = astDefinitions[_i4];
    if (def.kind === Kind.DIRECTIVE_DEFINITION) {
      var _def$arguments;
      var argsNodes = (_def$arguments = def.arguments) !== null && _def$arguments !== void 0 ? _def$arguments : [];
      directiveArgs[def.name.value] = argsNodes.map(function(arg) {
        return arg.name.value;
      });
    }
  }
  return {
    Directive: function Directive2(directiveNode) {
      var directiveName = directiveNode.name.value;
      var knownArgs = directiveArgs[directiveName];
      if (directiveNode.arguments && knownArgs) {
        for (var _i6 = 0, _directiveNode$argume2 = directiveNode.arguments; _i6 < _directiveNode$argume2.length; _i6++) {
          var argNode = _directiveNode$argume2[_i6];
          var argName = argNode.name.value;
          if (knownArgs.indexOf(argName) === -1) {
            var suggestions = suggestionList(argName, knownArgs);
            context.reportError(new GraphQLError('Unknown argument "'.concat(argName, '" on directive "@').concat(directiveName, '".') + didYouMean(suggestions), argNode));
          }
        }
      }
      return false;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueArgumentNamesRule.mjs
function UniqueArgumentNamesRule(context) {
  var knownArgNames = /* @__PURE__ */ Object.create(null);
  return {
    Field: function Field2() {
      knownArgNames = /* @__PURE__ */ Object.create(null);
    },
    Directive: function Directive2() {
      knownArgNames = /* @__PURE__ */ Object.create(null);
    },
    Argument: function Argument2(node) {
      var argName = node.name.value;
      if (knownArgNames[argName]) {
        context.reportError(new GraphQLError('There can be only one argument named "'.concat(argName, '".'), [knownArgNames[argName], node.name]));
      } else {
        knownArgNames[argName] = node.name;
      }
      return false;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/ValuesOfCorrectTypeRule.mjs
function ValuesOfCorrectTypeRule(context) {
  return {
    ListValue: function ListValue2(node) {
      var type = getNullableType(context.getParentInputType());
      if (!isListType(type)) {
        isValidValueNode(context, node);
        return false;
      }
    },
    ObjectValue: function ObjectValue2(node) {
      var type = getNamedType(context.getInputType());
      if (!isInputObjectType(type)) {
        isValidValueNode(context, node);
        return false;
      }
      var fieldNodeMap = keyMap(node.fields, function(field) {
        return field.name.value;
      });
      for (var _i2 = 0, _objectValues2 = objectValues_default(type.getFields()); _i2 < _objectValues2.length; _i2++) {
        var fieldDef = _objectValues2[_i2];
        var fieldNode = fieldNodeMap[fieldDef.name];
        if (!fieldNode && isRequiredInputField(fieldDef)) {
          var typeStr = inspect(fieldDef.type);
          context.reportError(new GraphQLError('Field "'.concat(type.name, ".").concat(fieldDef.name, '" of required type "').concat(typeStr, '" was not provided.'), node));
        }
      }
    },
    ObjectField: function ObjectField2(node) {
      var parentType = getNamedType(context.getParentInputType());
      var fieldType = context.getInputType();
      if (!fieldType && isInputObjectType(parentType)) {
        var suggestions = suggestionList(node.name.value, Object.keys(parentType.getFields()));
        context.reportError(new GraphQLError('Field "'.concat(node.name.value, '" is not defined by type "').concat(parentType.name, '".') + didYouMean(suggestions), node));
      }
    },
    NullValue: function NullValue2(node) {
      var type = context.getInputType();
      if (isNonNullType(type)) {
        context.reportError(new GraphQLError('Expected value of type "'.concat(inspect(type), '", found ').concat(print(node), "."), node));
      }
    },
    EnumValue: function EnumValue2(node) {
      return isValidValueNode(context, node);
    },
    IntValue: function IntValue2(node) {
      return isValidValueNode(context, node);
    },
    FloatValue: function FloatValue2(node) {
      return isValidValueNode(context, node);
    },
    StringValue: function StringValue2(node) {
      return isValidValueNode(context, node);
    },
    BooleanValue: function BooleanValue2(node) {
      return isValidValueNode(context, node);
    }
  };
}
function isValidValueNode(context, node) {
  var locationType = context.getInputType();
  if (!locationType) {
    return;
  }
  var type = getNamedType(locationType);
  if (!isLeafType(type)) {
    var typeStr = inspect(locationType);
    context.reportError(new GraphQLError('Expected value of type "'.concat(typeStr, '", found ').concat(print(node), "."), node));
    return;
  }
  try {
    var parseResult = type.parseLiteral(
      node,
      void 0
      /* variables */
    );
    if (parseResult === void 0) {
      var _typeStr = inspect(locationType);
      context.reportError(new GraphQLError('Expected value of type "'.concat(_typeStr, '", found ').concat(print(node), "."), node));
    }
  } catch (error) {
    var _typeStr2 = inspect(locationType);
    if (error instanceof GraphQLError) {
      context.reportError(error);
    } else {
      context.reportError(new GraphQLError('Expected value of type "'.concat(_typeStr2, '", found ').concat(print(node), "; ") + error.message, node, void 0, void 0, void 0, error));
    }
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/ProvidedRequiredArgumentsRule.mjs
function ownKeys3(object, enumerableOnly) {
  var keys = Object.keys(object);
  if (Object.getOwnPropertySymbols) {
    var symbols = Object.getOwnPropertySymbols(object);
    if (enumerableOnly) symbols = symbols.filter(function(sym) {
      return Object.getOwnPropertyDescriptor(object, sym).enumerable;
    });
    keys.push.apply(keys, symbols);
  }
  return keys;
}
function _objectSpread3(target) {
  for (var i = 1; i < arguments.length; i++) {
    var source = arguments[i] != null ? arguments[i] : {};
    if (i % 2) {
      ownKeys3(Object(source), true).forEach(function(key) {
        _defineProperty3(target, key, source[key]);
      });
    } else if (Object.getOwnPropertyDescriptors) {
      Object.defineProperties(target, Object.getOwnPropertyDescriptors(source));
    } else {
      ownKeys3(Object(source)).forEach(function(key) {
        Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
      });
    }
  }
  return target;
}
function _defineProperty3(obj, key, value) {
  if (key in obj) {
    Object.defineProperty(obj, key, { value, enumerable: true, configurable: true, writable: true });
  } else {
    obj[key] = value;
  }
  return obj;
}
function ProvidedRequiredArgumentsRule(context) {
  return _objectSpread3(_objectSpread3({}, ProvidedRequiredArgumentsOnDirectivesRule(context)), {}, {
    Field: {
      // Validate on leave to allow for deeper errors to appear first.
      leave: function leave(fieldNode) {
        var _fieldNode$arguments;
        var fieldDef = context.getFieldDef();
        if (!fieldDef) {
          return false;
        }
        var argNodes = (_fieldNode$arguments = fieldNode.arguments) !== null && _fieldNode$arguments !== void 0 ? _fieldNode$arguments : [];
        var argNodeMap = keyMap(argNodes, function(arg) {
          return arg.name.value;
        });
        for (var _i2 = 0, _fieldDef$args2 = fieldDef.args; _i2 < _fieldDef$args2.length; _i2++) {
          var argDef = _fieldDef$args2[_i2];
          var argNode = argNodeMap[argDef.name];
          if (!argNode && isRequiredArgument(argDef)) {
            var argTypeStr = inspect(argDef.type);
            context.reportError(new GraphQLError('Field "'.concat(fieldDef.name, '" argument "').concat(argDef.name, '" of type "').concat(argTypeStr, '" is required, but it was not provided.'), fieldNode));
          }
        }
      }
    }
  });
}
function ProvidedRequiredArgumentsOnDirectivesRule(context) {
  var requiredArgsMap = /* @__PURE__ */ Object.create(null);
  var schema = context.getSchema();
  var definedDirectives = schema ? schema.getDirectives() : specifiedDirectives;
  for (var _i4 = 0; _i4 < definedDirectives.length; _i4++) {
    var directive = definedDirectives[_i4];
    requiredArgsMap[directive.name] = keyMap(directive.args.filter(isRequiredArgument), function(arg) {
      return arg.name;
    });
  }
  var astDefinitions = context.getDocument().definitions;
  for (var _i6 = 0; _i6 < astDefinitions.length; _i6++) {
    var def = astDefinitions[_i6];
    if (def.kind === Kind.DIRECTIVE_DEFINITION) {
      var _def$arguments;
      var argNodes = (_def$arguments = def.arguments) !== null && _def$arguments !== void 0 ? _def$arguments : [];
      requiredArgsMap[def.name.value] = keyMap(argNodes.filter(isRequiredArgumentNode), function(arg) {
        return arg.name.value;
      });
    }
  }
  return {
    Directive: {
      // Validate on leave to allow for deeper errors to appear first.
      leave: function leave(directiveNode) {
        var directiveName = directiveNode.name.value;
        var requiredArgs = requiredArgsMap[directiveName];
        if (requiredArgs) {
          var _directiveNode$argume;
          var _argNodes = (_directiveNode$argume = directiveNode.arguments) !== null && _directiveNode$argume !== void 0 ? _directiveNode$argume : [];
          var argNodeMap = keyMap(_argNodes, function(arg) {
            return arg.name.value;
          });
          for (var _i8 = 0, _Object$keys2 = Object.keys(requiredArgs); _i8 < _Object$keys2.length; _i8++) {
            var argName = _Object$keys2[_i8];
            if (!argNodeMap[argName]) {
              var argType = requiredArgs[argName].type;
              var argTypeStr = isType(argType) ? inspect(argType) : print(argType);
              context.reportError(new GraphQLError('Directive "@'.concat(directiveName, '" argument "').concat(argName, '" of type "').concat(argTypeStr, '" is required, but it was not provided.'), directiveNode));
            }
          }
        }
      }
    }
  };
}
function isRequiredArgumentNode(arg) {
  return arg.type.kind === Kind.NON_NULL_TYPE && arg.defaultValue == null;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/VariablesInAllowedPositionRule.mjs
function VariablesInAllowedPositionRule(context) {
  var varDefMap = /* @__PURE__ */ Object.create(null);
  return {
    OperationDefinition: {
      enter: function enter() {
        varDefMap = /* @__PURE__ */ Object.create(null);
      },
      leave: function leave(operation) {
        var usages = context.getRecursiveVariableUsages(operation);
        for (var _i2 = 0; _i2 < usages.length; _i2++) {
          var _ref2 = usages[_i2];
          var node = _ref2.node;
          var type = _ref2.type;
          var defaultValue = _ref2.defaultValue;
          var varName = node.name.value;
          var varDef = varDefMap[varName];
          if (varDef && type) {
            var schema = context.getSchema();
            var varType = typeFromAST(schema, varDef.type);
            if (varType && !allowedVariableUsage(schema, varType, varDef.defaultValue, type, defaultValue)) {
              var varTypeStr = inspect(varType);
              var typeStr = inspect(type);
              context.reportError(new GraphQLError('Variable "$'.concat(varName, '" of type "').concat(varTypeStr, '" used in position expecting type "').concat(typeStr, '".'), [varDef, node]));
            }
          }
        }
      }
    },
    VariableDefinition: function VariableDefinition2(node) {
      varDefMap[node.variable.name.value] = node;
    }
  };
}
function allowedVariableUsage(schema, varType, varDefaultValue, locationType, locationDefaultValue) {
  if (isNonNullType(locationType) && !isNonNullType(varType)) {
    var hasNonNullVariableDefaultValue = varDefaultValue != null && varDefaultValue.kind !== Kind.NULL;
    var hasLocationDefaultValue = locationDefaultValue !== void 0;
    if (!hasNonNullVariableDefaultValue && !hasLocationDefaultValue) {
      return false;
    }
    var nullableLocationType = locationType.ofType;
    return isTypeSubTypeOf(schema, varType, nullableLocationType);
  }
  return isTypeSubTypeOf(schema, varType, locationType);
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/OverlappingFieldsCanBeMergedRule.mjs
function reasonMessage(reason) {
  if (Array.isArray(reason)) {
    return reason.map(function(_ref) {
      var responseName = _ref[0], subReason = _ref[1];
      return 'subfields "'.concat(responseName, '" conflict because ') + reasonMessage(subReason);
    }).join(" and ");
  }
  return reason;
}
function OverlappingFieldsCanBeMergedRule(context) {
  var comparedFragmentPairs = new PairSet();
  var cachedFieldsAndFragmentNames = /* @__PURE__ */ new Map();
  return {
    SelectionSet: function SelectionSet2(selectionSet) {
      var conflicts = findConflictsWithinSelectionSet(context, cachedFieldsAndFragmentNames, comparedFragmentPairs, context.getParentType(), selectionSet);
      for (var _i2 = 0; _i2 < conflicts.length; _i2++) {
        var _ref3 = conflicts[_i2];
        var _ref2$ = _ref3[0];
        var responseName = _ref2$[0];
        var reason = _ref2$[1];
        var fields1 = _ref3[1];
        var fields22 = _ref3[2];
        var reasonMsg = reasonMessage(reason);
        context.reportError(new GraphQLError('Fields "'.concat(responseName, '" conflict because ').concat(reasonMsg, ". Use different aliases on the fields to fetch both if this was intentional."), fields1.concat(fields22)));
      }
    }
  };
}
function findConflictsWithinSelectionSet(context, cachedFieldsAndFragmentNames, comparedFragmentPairs, parentType, selectionSet) {
  var conflicts = [];
  var _getFieldsAndFragment = getFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, parentType, selectionSet), fieldMap = _getFieldsAndFragment[0], fragmentNames = _getFieldsAndFragment[1];
  collectConflictsWithin(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, fieldMap);
  if (fragmentNames.length !== 0) {
    for (var i = 0; i < fragmentNames.length; i++) {
      collectConflictsBetweenFieldsAndFragment(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, false, fieldMap, fragmentNames[i]);
      for (var j = i + 1; j < fragmentNames.length; j++) {
        collectConflictsBetweenFragments(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, false, fragmentNames[i], fragmentNames[j]);
      }
    }
  }
  return conflicts;
}
function collectConflictsBetweenFieldsAndFragment(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fieldMap, fragmentName) {
  var fragment = context.getFragment(fragmentName);
  if (!fragment) {
    return;
  }
  var _getReferencedFieldsA = getReferencedFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, fragment), fieldMap2 = _getReferencedFieldsA[0], fragmentNames2 = _getReferencedFieldsA[1];
  if (fieldMap === fieldMap2) {
    return;
  }
  collectConflictsBetween(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fieldMap, fieldMap2);
  for (var i = 0; i < fragmentNames2.length; i++) {
    collectConflictsBetweenFieldsAndFragment(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fieldMap, fragmentNames2[i]);
  }
}
function collectConflictsBetweenFragments(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fragmentName1, fragmentName2) {
  if (fragmentName1 === fragmentName2) {
    return;
  }
  if (comparedFragmentPairs.has(fragmentName1, fragmentName2, areMutuallyExclusive)) {
    return;
  }
  comparedFragmentPairs.add(fragmentName1, fragmentName2, areMutuallyExclusive);
  var fragment1 = context.getFragment(fragmentName1);
  var fragment2 = context.getFragment(fragmentName2);
  if (!fragment1 || !fragment2) {
    return;
  }
  var _getReferencedFieldsA2 = getReferencedFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, fragment1), fieldMap1 = _getReferencedFieldsA2[0], fragmentNames1 = _getReferencedFieldsA2[1];
  var _getReferencedFieldsA3 = getReferencedFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, fragment2), fieldMap2 = _getReferencedFieldsA3[0], fragmentNames2 = _getReferencedFieldsA3[1];
  collectConflictsBetween(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fieldMap1, fieldMap2);
  for (var j = 0; j < fragmentNames2.length; j++) {
    collectConflictsBetweenFragments(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fragmentName1, fragmentNames2[j]);
  }
  for (var i = 0; i < fragmentNames1.length; i++) {
    collectConflictsBetweenFragments(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fragmentNames1[i], fragmentName2);
  }
}
function findConflictsBetweenSubSelectionSets(context, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, parentType1, selectionSet1, parentType2, selectionSet2) {
  var conflicts = [];
  var _getFieldsAndFragment2 = getFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, parentType1, selectionSet1), fieldMap1 = _getFieldsAndFragment2[0], fragmentNames1 = _getFieldsAndFragment2[1];
  var _getFieldsAndFragment3 = getFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, parentType2, selectionSet2), fieldMap2 = _getFieldsAndFragment3[0], fragmentNames2 = _getFieldsAndFragment3[1];
  collectConflictsBetween(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fieldMap1, fieldMap2);
  if (fragmentNames2.length !== 0) {
    for (var j = 0; j < fragmentNames2.length; j++) {
      collectConflictsBetweenFieldsAndFragment(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fieldMap1, fragmentNames2[j]);
    }
  }
  if (fragmentNames1.length !== 0) {
    for (var i = 0; i < fragmentNames1.length; i++) {
      collectConflictsBetweenFieldsAndFragment(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fieldMap2, fragmentNames1[i]);
    }
  }
  for (var _i3 = 0; _i3 < fragmentNames1.length; _i3++) {
    for (var _j = 0; _j < fragmentNames2.length; _j++) {
      collectConflictsBetweenFragments(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, fragmentNames1[_i3], fragmentNames2[_j]);
    }
  }
  return conflicts;
}
function collectConflictsWithin(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, fieldMap) {
  for (var _i5 = 0, _objectEntries2 = objectEntries_default(fieldMap); _i5 < _objectEntries2.length; _i5++) {
    var _ref5 = _objectEntries2[_i5];
    var responseName = _ref5[0];
    var fields7 = _ref5[1];
    if (fields7.length > 1) {
      for (var i = 0; i < fields7.length; i++) {
        for (var j = i + 1; j < fields7.length; j++) {
          var conflict = findConflict(
            context,
            cachedFieldsAndFragmentNames,
            comparedFragmentPairs,
            false,
            // within one collection is never mutually exclusive
            responseName,
            fields7[i],
            fields7[j]
          );
          if (conflict) {
            conflicts.push(conflict);
          }
        }
      }
    }
  }
}
function collectConflictsBetween(context, conflicts, cachedFieldsAndFragmentNames, comparedFragmentPairs, parentFieldsAreMutuallyExclusive, fieldMap1, fieldMap2) {
  for (var _i7 = 0, _Object$keys2 = Object.keys(fieldMap1); _i7 < _Object$keys2.length; _i7++) {
    var responseName = _Object$keys2[_i7];
    var fields22 = fieldMap2[responseName];
    if (fields22) {
      var fields1 = fieldMap1[responseName];
      for (var i = 0; i < fields1.length; i++) {
        for (var j = 0; j < fields22.length; j++) {
          var conflict = findConflict(context, cachedFieldsAndFragmentNames, comparedFragmentPairs, parentFieldsAreMutuallyExclusive, responseName, fields1[i], fields22[j]);
          if (conflict) {
            conflicts.push(conflict);
          }
        }
      }
    }
  }
}
function findConflict(context, cachedFieldsAndFragmentNames, comparedFragmentPairs, parentFieldsAreMutuallyExclusive, responseName, field1, field2) {
  var parentType1 = field1[0], node1 = field1[1], def1 = field1[2];
  var parentType2 = field2[0], node2 = field2[1], def2 = field2[2];
  var areMutuallyExclusive = parentFieldsAreMutuallyExclusive || parentType1 !== parentType2 && isObjectType(parentType1) && isObjectType(parentType2);
  if (!areMutuallyExclusive) {
    var _node1$arguments, _node2$arguments;
    var name1 = node1.name.value;
    var name2 = node2.name.value;
    if (name1 !== name2) {
      return [[responseName, '"'.concat(name1, '" and "').concat(name2, '" are different fields')], [node1], [node2]];
    }
    var args1 = (_node1$arguments = node1.arguments) !== null && _node1$arguments !== void 0 ? _node1$arguments : [];
    var args2 = (_node2$arguments = node2.arguments) !== null && _node2$arguments !== void 0 ? _node2$arguments : [];
    if (!sameArguments(args1, args2)) {
      return [[responseName, "they have differing arguments"], [node1], [node2]];
    }
  }
  var type1 = def1 === null || def1 === void 0 ? void 0 : def1.type;
  var type2 = def2 === null || def2 === void 0 ? void 0 : def2.type;
  if (type1 && type2 && doTypesConflict(type1, type2)) {
    return [[responseName, 'they return conflicting types "'.concat(inspect(type1), '" and "').concat(inspect(type2), '"')], [node1], [node2]];
  }
  var selectionSet1 = node1.selectionSet;
  var selectionSet2 = node2.selectionSet;
  if (selectionSet1 && selectionSet2) {
    var conflicts = findConflictsBetweenSubSelectionSets(context, cachedFieldsAndFragmentNames, comparedFragmentPairs, areMutuallyExclusive, getNamedType(type1), selectionSet1, getNamedType(type2), selectionSet2);
    return subfieldConflicts(conflicts, responseName, node1, node2);
  }
}
function sameArguments(arguments1, arguments2) {
  if (arguments1.length !== arguments2.length) {
    return false;
  }
  return arguments1.every(function(argument1) {
    var argument2 = find_default(arguments2, function(argument) {
      return argument.name.value === argument1.name.value;
    });
    if (!argument2) {
      return false;
    }
    return sameValue(argument1.value, argument2.value);
  });
}
function sameValue(value1, value2) {
  return print(value1) === print(value2);
}
function doTypesConflict(type1, type2) {
  if (isListType(type1)) {
    return isListType(type2) ? doTypesConflict(type1.ofType, type2.ofType) : true;
  }
  if (isListType(type2)) {
    return true;
  }
  if (isNonNullType(type1)) {
    return isNonNullType(type2) ? doTypesConflict(type1.ofType, type2.ofType) : true;
  }
  if (isNonNullType(type2)) {
    return true;
  }
  if (isLeafType(type1) || isLeafType(type2)) {
    return type1 !== type2;
  }
  return false;
}
function getFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, parentType, selectionSet) {
  var cached = cachedFieldsAndFragmentNames.get(selectionSet);
  if (!cached) {
    var nodeAndDefs = /* @__PURE__ */ Object.create(null);
    var fragmentNames = /* @__PURE__ */ Object.create(null);
    _collectFieldsAndFragmentNames(context, parentType, selectionSet, nodeAndDefs, fragmentNames);
    cached = [nodeAndDefs, Object.keys(fragmentNames)];
    cachedFieldsAndFragmentNames.set(selectionSet, cached);
  }
  return cached;
}
function getReferencedFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, fragment) {
  var cached = cachedFieldsAndFragmentNames.get(fragment.selectionSet);
  if (cached) {
    return cached;
  }
  var fragmentType = typeFromAST(context.getSchema(), fragment.typeCondition);
  return getFieldsAndFragmentNames(context, cachedFieldsAndFragmentNames, fragmentType, fragment.selectionSet);
}
function _collectFieldsAndFragmentNames(context, parentType, selectionSet, nodeAndDefs, fragmentNames) {
  for (var _i9 = 0, _selectionSet$selecti2 = selectionSet.selections; _i9 < _selectionSet$selecti2.length; _i9++) {
    var selection = _selectionSet$selecti2[_i9];
    switch (selection.kind) {
      case Kind.FIELD: {
        var fieldName = selection.name.value;
        var fieldDef = void 0;
        if (isObjectType(parentType) || isInterfaceType(parentType)) {
          fieldDef = parentType.getFields()[fieldName];
        }
        var responseName = selection.alias ? selection.alias.value : fieldName;
        if (!nodeAndDefs[responseName]) {
          nodeAndDefs[responseName] = [];
        }
        nodeAndDefs[responseName].push([parentType, selection, fieldDef]);
        break;
      }
      case Kind.FRAGMENT_SPREAD:
        fragmentNames[selection.name.value] = true;
        break;
      case Kind.INLINE_FRAGMENT: {
        var typeCondition = selection.typeCondition;
        var inlineFragmentType = typeCondition ? typeFromAST(context.getSchema(), typeCondition) : parentType;
        _collectFieldsAndFragmentNames(context, inlineFragmentType, selection.selectionSet, nodeAndDefs, fragmentNames);
        break;
      }
    }
  }
}
function subfieldConflicts(conflicts, responseName, node1, node2) {
  if (conflicts.length > 0) {
    return [[responseName, conflicts.map(function(_ref6) {
      var reason = _ref6[0];
      return reason;
    })], conflicts.reduce(function(allFields, _ref7) {
      var fields1 = _ref7[1];
      return allFields.concat(fields1);
    }, [node1]), conflicts.reduce(function(allFields, _ref8) {
      var fields22 = _ref8[2];
      return allFields.concat(fields22);
    }, [node2])];
  }
}
var PairSet = function() {
  function PairSet2() {
    this._data = /* @__PURE__ */ Object.create(null);
  }
  var _proto = PairSet2.prototype;
  _proto.has = function has(a, b, areMutuallyExclusive) {
    var first = this._data[a];
    var result = first && first[b];
    if (result === void 0) {
      return false;
    }
    if (areMutuallyExclusive === false) {
      return result === false;
    }
    return true;
  };
  _proto.add = function add(a, b, areMutuallyExclusive) {
    this._pairSetAdd(a, b, areMutuallyExclusive);
    this._pairSetAdd(b, a, areMutuallyExclusive);
  };
  _proto._pairSetAdd = function _pairSetAdd(a, b, areMutuallyExclusive) {
    var map2 = this._data[a];
    if (!map2) {
      map2 = /* @__PURE__ */ Object.create(null);
      this._data[a] = map2;
    }
    map2[b] = areMutuallyExclusive;
  };
  return PairSet2;
}();

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueInputFieldNamesRule.mjs
function UniqueInputFieldNamesRule(context) {
  var knownNameStack = [];
  var knownNames = /* @__PURE__ */ Object.create(null);
  return {
    ObjectValue: {
      enter: function enter() {
        knownNameStack.push(knownNames);
        knownNames = /* @__PURE__ */ Object.create(null);
      },
      leave: function leave() {
        knownNames = knownNameStack.pop();
      }
    },
    ObjectField: function ObjectField2(node) {
      var fieldName = node.name.value;
      if (knownNames[fieldName]) {
        context.reportError(new GraphQLError('There can be only one input field named "'.concat(fieldName, '".'), [knownNames[fieldName], node.name]));
      } else {
        knownNames[fieldName] = node.name;
      }
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/LoneSchemaDefinitionRule.mjs
function LoneSchemaDefinitionRule(context) {
  var _ref, _ref2, _oldSchema$astNode;
  var oldSchema = context.getSchema();
  var alreadyDefined = (_ref = (_ref2 = (_oldSchema$astNode = oldSchema === null || oldSchema === void 0 ? void 0 : oldSchema.astNode) !== null && _oldSchema$astNode !== void 0 ? _oldSchema$astNode : oldSchema === null || oldSchema === void 0 ? void 0 : oldSchema.getQueryType()) !== null && _ref2 !== void 0 ? _ref2 : oldSchema === null || oldSchema === void 0 ? void 0 : oldSchema.getMutationType()) !== null && _ref !== void 0 ? _ref : oldSchema === null || oldSchema === void 0 ? void 0 : oldSchema.getSubscriptionType();
  var schemaDefinitionsCount = 0;
  return {
    SchemaDefinition: function SchemaDefinition(node) {
      if (alreadyDefined) {
        context.reportError(new GraphQLError("Cannot define a new schema within a schema extension.", node));
        return;
      }
      if (schemaDefinitionsCount > 0) {
        context.reportError(new GraphQLError("Must provide only one schema definition.", node));
      }
      ++schemaDefinitionsCount;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueOperationTypesRule.mjs
function UniqueOperationTypesRule(context) {
  var schema = context.getSchema();
  var definedOperationTypes = /* @__PURE__ */ Object.create(null);
  var existingOperationTypes = schema ? {
    query: schema.getQueryType(),
    mutation: schema.getMutationType(),
    subscription: schema.getSubscriptionType()
  } : {};
  return {
    SchemaDefinition: checkOperationTypes,
    SchemaExtension: checkOperationTypes
  };
  function checkOperationTypes(node) {
    var _node$operationTypes;
    var operationTypesNodes = (_node$operationTypes = node.operationTypes) !== null && _node$operationTypes !== void 0 ? _node$operationTypes : [];
    for (var _i2 = 0; _i2 < operationTypesNodes.length; _i2++) {
      var operationType = operationTypesNodes[_i2];
      var operation = operationType.operation;
      var alreadyDefinedOperationType = definedOperationTypes[operation];
      if (existingOperationTypes[operation]) {
        context.reportError(new GraphQLError("Type for ".concat(operation, " already defined in the schema. It cannot be redefined."), operationType));
      } else if (alreadyDefinedOperationType) {
        context.reportError(new GraphQLError("There can be only one ".concat(operation, " type in schema."), [alreadyDefinedOperationType, operationType]));
      } else {
        definedOperationTypes[operation] = operationType;
      }
    }
    return false;
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueTypeNamesRule.mjs
function UniqueTypeNamesRule(context) {
  var knownTypeNames = /* @__PURE__ */ Object.create(null);
  var schema = context.getSchema();
  return {
    ScalarTypeDefinition: checkTypeName,
    ObjectTypeDefinition: checkTypeName,
    InterfaceTypeDefinition: checkTypeName,
    UnionTypeDefinition: checkTypeName,
    EnumTypeDefinition: checkTypeName,
    InputObjectTypeDefinition: checkTypeName
  };
  function checkTypeName(node) {
    var typeName = node.name.value;
    if (schema !== null && schema !== void 0 && schema.getType(typeName)) {
      context.reportError(new GraphQLError('Type "'.concat(typeName, '" already exists in the schema. It cannot also be defined in this type definition.'), node.name));
      return;
    }
    if (knownTypeNames[typeName]) {
      context.reportError(new GraphQLError('There can be only one type named "'.concat(typeName, '".'), [knownTypeNames[typeName], node.name]));
    } else {
      knownTypeNames[typeName] = node.name;
    }
    return false;
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueEnumValueNamesRule.mjs
function UniqueEnumValueNamesRule(context) {
  var schema = context.getSchema();
  var existingTypeMap = schema ? schema.getTypeMap() : /* @__PURE__ */ Object.create(null);
  var knownValueNames = /* @__PURE__ */ Object.create(null);
  return {
    EnumTypeDefinition: checkValueUniqueness,
    EnumTypeExtension: checkValueUniqueness
  };
  function checkValueUniqueness(node) {
    var _node$values;
    var typeName = node.name.value;
    if (!knownValueNames[typeName]) {
      knownValueNames[typeName] = /* @__PURE__ */ Object.create(null);
    }
    var valueNodes = (_node$values = node.values) !== null && _node$values !== void 0 ? _node$values : [];
    var valueNames = knownValueNames[typeName];
    for (var _i2 = 0; _i2 < valueNodes.length; _i2++) {
      var valueDef = valueNodes[_i2];
      var valueName = valueDef.name.value;
      var existingType = existingTypeMap[typeName];
      if (isEnumType(existingType) && existingType.getValue(valueName)) {
        context.reportError(new GraphQLError('Enum value "'.concat(typeName, ".").concat(valueName, '" already exists in the schema. It cannot also be defined in this type extension.'), valueDef.name));
      } else if (valueNames[valueName]) {
        context.reportError(new GraphQLError('Enum value "'.concat(typeName, ".").concat(valueName, '" can only be defined once.'), [valueNames[valueName], valueDef.name]));
      } else {
        valueNames[valueName] = valueDef.name;
      }
    }
    return false;
  }
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueFieldDefinitionNamesRule.mjs
function UniqueFieldDefinitionNamesRule(context) {
  var schema = context.getSchema();
  var existingTypeMap = schema ? schema.getTypeMap() : /* @__PURE__ */ Object.create(null);
  var knownFieldNames = /* @__PURE__ */ Object.create(null);
  return {
    InputObjectTypeDefinition: checkFieldUniqueness,
    InputObjectTypeExtension: checkFieldUniqueness,
    InterfaceTypeDefinition: checkFieldUniqueness,
    InterfaceTypeExtension: checkFieldUniqueness,
    ObjectTypeDefinition: checkFieldUniqueness,
    ObjectTypeExtension: checkFieldUniqueness
  };
  function checkFieldUniqueness(node) {
    var _node$fields;
    var typeName = node.name.value;
    if (!knownFieldNames[typeName]) {
      knownFieldNames[typeName] = /* @__PURE__ */ Object.create(null);
    }
    var fieldNodes = (_node$fields = node.fields) !== null && _node$fields !== void 0 ? _node$fields : [];
    var fieldNames = knownFieldNames[typeName];
    for (var _i2 = 0; _i2 < fieldNodes.length; _i2++) {
      var fieldDef = fieldNodes[_i2];
      var fieldName = fieldDef.name.value;
      if (hasField(existingTypeMap[typeName], fieldName)) {
        context.reportError(new GraphQLError('Field "'.concat(typeName, ".").concat(fieldName, '" already exists in the schema. It cannot also be defined in this type extension.'), fieldDef.name));
      } else if (fieldNames[fieldName]) {
        context.reportError(new GraphQLError('Field "'.concat(typeName, ".").concat(fieldName, '" can only be defined once.'), [fieldNames[fieldName], fieldDef.name]));
      } else {
        fieldNames[fieldName] = fieldDef.name;
      }
    }
    return false;
  }
}
function hasField(type, fieldName) {
  if (isObjectType(type) || isInterfaceType(type) || isInputObjectType(type)) {
    return type.getFields()[fieldName] != null;
  }
  return false;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/UniqueDirectiveNamesRule.mjs
function UniqueDirectiveNamesRule(context) {
  var knownDirectiveNames = /* @__PURE__ */ Object.create(null);
  var schema = context.getSchema();
  return {
    DirectiveDefinition: function DirectiveDefinition(node) {
      var directiveName = node.name.value;
      if (schema !== null && schema !== void 0 && schema.getDirective(directiveName)) {
        context.reportError(new GraphQLError('Directive "@'.concat(directiveName, '" already exists in the schema. It cannot be redefined.'), node.name));
        return;
      }
      if (knownDirectiveNames[directiveName]) {
        context.reportError(new GraphQLError('There can be only one directive named "@'.concat(directiveName, '".'), [knownDirectiveNames[directiveName], node.name]));
      } else {
        knownDirectiveNames[directiveName] = node.name;
      }
      return false;
    }
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/rules/PossibleTypeExtensionsRule.mjs
var _defKindToExtKind;
function _defineProperty4(obj, key, value) {
  if (key in obj) {
    Object.defineProperty(obj, key, { value, enumerable: true, configurable: true, writable: true });
  } else {
    obj[key] = value;
  }
  return obj;
}
function PossibleTypeExtensionsRule(context) {
  var schema = context.getSchema();
  var definedTypes = /* @__PURE__ */ Object.create(null);
  for (var _i2 = 0, _context$getDocument$2 = context.getDocument().definitions; _i2 < _context$getDocument$2.length; _i2++) {
    var def = _context$getDocument$2[_i2];
    if (isTypeDefinitionNode(def)) {
      definedTypes[def.name.value] = def;
    }
  }
  return {
    ScalarTypeExtension: checkExtension,
    ObjectTypeExtension: checkExtension,
    InterfaceTypeExtension: checkExtension,
    UnionTypeExtension: checkExtension,
    EnumTypeExtension: checkExtension,
    InputObjectTypeExtension: checkExtension
  };
  function checkExtension(node) {
    var typeName = node.name.value;
    var defNode = definedTypes[typeName];
    var existingType = schema === null || schema === void 0 ? void 0 : schema.getType(typeName);
    var expectedKind;
    if (defNode) {
      expectedKind = defKindToExtKind[defNode.kind];
    } else if (existingType) {
      expectedKind = typeToExtKind(existingType);
    }
    if (expectedKind) {
      if (expectedKind !== node.kind) {
        var kindStr = extensionKindToTypeName(node.kind);
        context.reportError(new GraphQLError("Cannot extend non-".concat(kindStr, ' type "').concat(typeName, '".'), defNode ? [defNode, node] : node));
      }
    } else {
      var allTypeNames = Object.keys(definedTypes);
      if (schema) {
        allTypeNames = allTypeNames.concat(Object.keys(schema.getTypeMap()));
      }
      var suggestedTypes = suggestionList(typeName, allTypeNames);
      context.reportError(new GraphQLError('Cannot extend type "'.concat(typeName, '" because it is not defined.') + didYouMean(suggestedTypes), node.name));
    }
  }
}
var defKindToExtKind = (_defKindToExtKind = {}, _defineProperty4(_defKindToExtKind, Kind.SCALAR_TYPE_DEFINITION, Kind.SCALAR_TYPE_EXTENSION), _defineProperty4(_defKindToExtKind, Kind.OBJECT_TYPE_DEFINITION, Kind.OBJECT_TYPE_EXTENSION), _defineProperty4(_defKindToExtKind, Kind.INTERFACE_TYPE_DEFINITION, Kind.INTERFACE_TYPE_EXTENSION), _defineProperty4(_defKindToExtKind, Kind.UNION_TYPE_DEFINITION, Kind.UNION_TYPE_EXTENSION), _defineProperty4(_defKindToExtKind, Kind.ENUM_TYPE_DEFINITION, Kind.ENUM_TYPE_EXTENSION), _defineProperty4(_defKindToExtKind, Kind.INPUT_OBJECT_TYPE_DEFINITION, Kind.INPUT_OBJECT_TYPE_EXTENSION), _defKindToExtKind);
function typeToExtKind(type) {
  if (isScalarType(type)) {
    return Kind.SCALAR_TYPE_EXTENSION;
  }
  if (isObjectType(type)) {
    return Kind.OBJECT_TYPE_EXTENSION;
  }
  if (isInterfaceType(type)) {
    return Kind.INTERFACE_TYPE_EXTENSION;
  }
  if (isUnionType(type)) {
    return Kind.UNION_TYPE_EXTENSION;
  }
  if (isEnumType(type)) {
    return Kind.ENUM_TYPE_EXTENSION;
  }
  if (isInputObjectType(type)) {
    return Kind.INPUT_OBJECT_TYPE_EXTENSION;
  }
  invariant(0, "Unexpected type: " + inspect(type));
}
function extensionKindToTypeName(kind) {
  switch (kind) {
    case Kind.SCALAR_TYPE_EXTENSION:
      return "scalar";
    case Kind.OBJECT_TYPE_EXTENSION:
      return "object";
    case Kind.INTERFACE_TYPE_EXTENSION:
      return "interface";
    case Kind.UNION_TYPE_EXTENSION:
      return "union";
    case Kind.ENUM_TYPE_EXTENSION:
      return "enum";
    case Kind.INPUT_OBJECT_TYPE_EXTENSION:
      return "input object";
  }
  invariant(0, "Unexpected kind: " + inspect(kind));
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/specifiedRules.mjs
var specifiedRules = Object.freeze([ExecutableDefinitionsRule, UniqueOperationNamesRule, LoneAnonymousOperationRule, SingleFieldSubscriptionsRule, KnownTypeNamesRule, FragmentsOnCompositeTypesRule, VariablesAreInputTypesRule, ScalarLeafsRule, FieldsOnCorrectTypeRule, UniqueFragmentNamesRule, KnownFragmentNamesRule, NoUnusedFragmentsRule, PossibleFragmentSpreadsRule, NoFragmentCyclesRule, UniqueVariableNamesRule, NoUndefinedVariablesRule, NoUnusedVariablesRule, KnownDirectivesRule, UniqueDirectivesPerLocationRule, KnownArgumentNamesRule, UniqueArgumentNamesRule, ValuesOfCorrectTypeRule, ProvidedRequiredArgumentsRule, VariablesInAllowedPositionRule, OverlappingFieldsCanBeMergedRule, UniqueInputFieldNamesRule]);
var specifiedSDLRules = Object.freeze([LoneSchemaDefinitionRule, UniqueOperationTypesRule, UniqueTypeNamesRule, UniqueEnumValueNamesRule, UniqueFieldDefinitionNamesRule, UniqueDirectiveNamesRule, KnownTypeNamesRule, KnownDirectivesRule, UniqueDirectivesPerLocationRule, PossibleTypeExtensionsRule, KnownArgumentNamesOnDirectivesRule, UniqueArgumentNamesRule, UniqueInputFieldNamesRule, ProvidedRequiredArgumentsOnDirectivesRule]);

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/validation/ValidationContext.mjs
function _inheritsLoose(subClass, superClass) {
  subClass.prototype = Object.create(superClass.prototype);
  subClass.prototype.constructor = subClass;
  subClass.__proto__ = superClass;
}
var ASTValidationContext = function() {
  function ASTValidationContext2(ast, onError) {
    this._ast = ast;
    this._fragments = void 0;
    this._fragmentSpreads = /* @__PURE__ */ new Map();
    this._recursivelyReferencedFragments = /* @__PURE__ */ new Map();
    this._onError = onError;
  }
  var _proto = ASTValidationContext2.prototype;
  _proto.reportError = function reportError(error) {
    this._onError(error);
  };
  _proto.getDocument = function getDocument() {
    return this._ast;
  };
  _proto.getFragment = function getFragment(name) {
    var fragments = this._fragments;
    if (!fragments) {
      this._fragments = fragments = this.getDocument().definitions.reduce(function(frags, statement) {
        if (statement.kind === Kind.FRAGMENT_DEFINITION) {
          frags[statement.name.value] = statement;
        }
        return frags;
      }, /* @__PURE__ */ Object.create(null));
    }
    return fragments[name];
  };
  _proto.getFragmentSpreads = function getFragmentSpreads(node) {
    var spreads = this._fragmentSpreads.get(node);
    if (!spreads) {
      spreads = [];
      var setsToVisit = [node];
      while (setsToVisit.length !== 0) {
        var set = setsToVisit.pop();
        for (var _i2 = 0, _set$selections2 = set.selections; _i2 < _set$selections2.length; _i2++) {
          var selection = _set$selections2[_i2];
          if (selection.kind === Kind.FRAGMENT_SPREAD) {
            spreads.push(selection);
          } else if (selection.selectionSet) {
            setsToVisit.push(selection.selectionSet);
          }
        }
      }
      this._fragmentSpreads.set(node, spreads);
    }
    return spreads;
  };
  _proto.getRecursivelyReferencedFragments = function getRecursivelyReferencedFragments(operation) {
    var fragments = this._recursivelyReferencedFragments.get(operation);
    if (!fragments) {
      fragments = [];
      var collectedNames = /* @__PURE__ */ Object.create(null);
      var nodesToVisit = [operation.selectionSet];
      while (nodesToVisit.length !== 0) {
        var node = nodesToVisit.pop();
        for (var _i4 = 0, _this$getFragmentSpre2 = this.getFragmentSpreads(node); _i4 < _this$getFragmentSpre2.length; _i4++) {
          var spread = _this$getFragmentSpre2[_i4];
          var fragName = spread.name.value;
          if (collectedNames[fragName] !== true) {
            collectedNames[fragName] = true;
            var fragment = this.getFragment(fragName);
            if (fragment) {
              fragments.push(fragment);
              nodesToVisit.push(fragment.selectionSet);
            }
          }
        }
      }
      this._recursivelyReferencedFragments.set(operation, fragments);
    }
    return fragments;
  };
  return ASTValidationContext2;
}();
var SDLValidationContext = function(_ASTValidationContext) {
  _inheritsLoose(SDLValidationContext2, _ASTValidationContext);
  function SDLValidationContext2(ast, schema, onError) {
    var _this;
    _this = _ASTValidationContext.call(this, ast, onError) || this;
    _this._schema = schema;
    return _this;
  }
  var _proto2 = SDLValidationContext2.prototype;
  _proto2.getSchema = function getSchema() {
    return this._schema;
  };
  return SDLValidationContext2;
}(ASTValidationContext);
var ValidationContext = function(_ASTValidationContext2) {
  _inheritsLoose(ValidationContext2, _ASTValidationContext2);
  function ValidationContext2(schema, ast, typeInfo, onError) {
    var _this2;
    _this2 = _ASTValidationContext2.call(this, ast, onError) || this;
    _this2._schema = schema;
    _this2._typeInfo = typeInfo;
    _this2._variableUsages = /* @__PURE__ */ new Map();
    _this2._recursiveVariableUsages = /* @__PURE__ */ new Map();
    return _this2;
  }
  var _proto3 = ValidationContext2.prototype;
  _proto3.getSchema = function getSchema() {
    return this._schema;
  };
  _proto3.getVariableUsages = function getVariableUsages(node) {
    var usages = this._variableUsages.get(node);
    if (!usages) {
      var newUsages = [];
      var typeInfo = new TypeInfo(this._schema);
      visit(node, visitWithTypeInfo(typeInfo, {
        VariableDefinition: function VariableDefinition2() {
          return false;
        },
        Variable: function Variable2(variable) {
          newUsages.push({
            node: variable,
            type: typeInfo.getInputType(),
            defaultValue: typeInfo.getDefaultValue()
          });
        }
      }));
      usages = newUsages;
      this._variableUsages.set(node, usages);
    }
    return usages;
  };
  _proto3.getRecursiveVariableUsages = function getRecursiveVariableUsages(operation) {
    var usages = this._recursiveVariableUsages.get(operation);
    if (!usages) {
      usages = this.getVariableUsages(operation);
      for (var _i6 = 0, _this$getRecursivelyR2 = this.getRecursivelyReferencedFragments(operation); _i6 < _this$getRecursivelyR2.length; _i6++) {
        var frag = _this$getRecursivelyR2[_i6];
        usages = usages.concat(this.getVariableUsages(frag));
      }
      this._recursiveVariableUsages.set(operation, usages);
    }
    return usages;
  };
  _proto3.getType = function getType() {
    return this._typeInfo.getType();
  };
  _proto3.getParentType = function getParentType() {
    return this._typeInfo.getParentType();
  };
  _proto3.getInputType = function getInputType() {
    return this._typeInfo.getInputType();
  };
  _proto3.getParentInputType = function getParentInputType() {
    return this._typeInfo.getParentInputType();
  };
  _proto3.getFieldDef = function getFieldDef3() {
    return this._typeInfo.getFieldDef();
  };
  _proto3.getDirective = function getDirective() {
    return this._typeInfo.getDirective();
  };
  _proto3.getArgument = function getArgument() {
    return this._typeInfo.getArgument();
  };
  _proto3.getEnumValue = function getEnumValue() {
    return this._typeInfo.getEnumValue();
  };
  return ValidationContext2;
}(ASTValidationContext);

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/jsutils/memoize3.mjs
function memoize3(fn) {
  var cache0;
  return function memoized(a1, a2, a3) {
    if (!cache0) {
      cache0 = /* @__PURE__ */ new WeakMap();
    }
    var cache1 = cache0.get(a1);
    var cache2;
    if (cache1) {
      cache2 = cache1.get(a2);
      if (cache2) {
        var cachedValue = cache2.get(a3);
        if (cachedValue !== void 0) {
          return cachedValue;
        }
      }
    } else {
      cache1 = /* @__PURE__ */ new WeakMap();
      cache0.set(a1, cache1);
    }
    if (!cache2) {
      cache2 = /* @__PURE__ */ new WeakMap();
      cache1.set(a2, cache2);
    }
    var newValue = fn(a1, a2, a3);
    cache2.set(a3, newValue);
    return newValue;
  };
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/valueFromAST.mjs
function valueFromAST(valueNode, type, variables) {
  if (!valueNode) {
    return;
  }
  if (valueNode.kind === Kind.VARIABLE) {
    var variableName = valueNode.name.value;
    if (variables == null || variables[variableName] === void 0) {
      return;
    }
    var variableValue = variables[variableName];
    if (variableValue === null && isNonNullType(type)) {
      return;
    }
    return variableValue;
  }
  if (isNonNullType(type)) {
    if (valueNode.kind === Kind.NULL) {
      return;
    }
    return valueFromAST(valueNode, type.ofType, variables);
  }
  if (valueNode.kind === Kind.NULL) {
    return null;
  }
  if (isListType(type)) {
    var itemType = type.ofType;
    if (valueNode.kind === Kind.LIST) {
      var coercedValues = [];
      for (var _i2 = 0, _valueNode$values2 = valueNode.values; _i2 < _valueNode$values2.length; _i2++) {
        var itemNode = _valueNode$values2[_i2];
        if (isMissingVariable(itemNode, variables)) {
          if (isNonNullType(itemType)) {
            return;
          }
          coercedValues.push(null);
        } else {
          var itemValue = valueFromAST(itemNode, itemType, variables);
          if (itemValue === void 0) {
            return;
          }
          coercedValues.push(itemValue);
        }
      }
      return coercedValues;
    }
    var coercedValue = valueFromAST(valueNode, itemType, variables);
    if (coercedValue === void 0) {
      return;
    }
    return [coercedValue];
  }
  if (isInputObjectType(type)) {
    if (valueNode.kind !== Kind.OBJECT) {
      return;
    }
    var coercedObj = /* @__PURE__ */ Object.create(null);
    var fieldNodes = keyMap(valueNode.fields, function(field2) {
      return field2.name.value;
    });
    for (var _i4 = 0, _objectValues2 = objectValues_default(type.getFields()); _i4 < _objectValues2.length; _i4++) {
      var field = _objectValues2[_i4];
      var fieldNode = fieldNodes[field.name];
      if (!fieldNode || isMissingVariable(fieldNode.value, variables)) {
        if (field.defaultValue !== void 0) {
          coercedObj[field.name] = field.defaultValue;
        } else if (isNonNullType(field.type)) {
          return;
        }
        continue;
      }
      var fieldValue = valueFromAST(fieldNode.value, field.type, variables);
      if (fieldValue === void 0) {
        return;
      }
      coercedObj[field.name] = fieldValue;
    }
    return coercedObj;
  }
  if (isLeafType(type)) {
    var result;
    try {
      result = type.parseLiteral(valueNode, variables);
    } catch (_error) {
      return;
    }
    if (result === void 0) {
      return;
    }
    return result;
  }
  invariant(0, "Unexpected input type: " + inspect(type));
}
function isMissingVariable(valueNode, variables) {
  return valueNode.kind === Kind.VARIABLE && (variables == null || variables[valueNode.name.value] === void 0);
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/execution/values.mjs
function getArgumentValues(def, node, variableValues) {
  var _node$arguments;
  var coercedValues = {};
  var argumentNodes = (_node$arguments = node.arguments) !== null && _node$arguments !== void 0 ? _node$arguments : [];
  var argNodeMap = keyMap(argumentNodes, function(arg) {
    return arg.name.value;
  });
  for (var _i4 = 0, _def$args2 = def.args; _i4 < _def$args2.length; _i4++) {
    var argDef = _def$args2[_i4];
    var name = argDef.name;
    var argType = argDef.type;
    var argumentNode = argNodeMap[name];
    if (!argumentNode) {
      if (argDef.defaultValue !== void 0) {
        coercedValues[name] = argDef.defaultValue;
      } else if (isNonNullType(argType)) {
        throw new GraphQLError('Argument "'.concat(name, '" of required type "').concat(inspect(argType), '" ') + "was not provided.", node);
      }
      continue;
    }
    var valueNode = argumentNode.value;
    var isNull = valueNode.kind === Kind.NULL;
    if (valueNode.kind === Kind.VARIABLE) {
      var variableName = valueNode.name.value;
      if (variableValues == null || !hasOwnProperty(variableValues, variableName)) {
        if (argDef.defaultValue !== void 0) {
          coercedValues[name] = argDef.defaultValue;
        } else if (isNonNullType(argType)) {
          throw new GraphQLError('Argument "'.concat(name, '" of required type "').concat(inspect(argType), '" ') + 'was provided the variable "$'.concat(variableName, '" which was not provided a runtime value.'), valueNode);
        }
        continue;
      }
      isNull = variableValues[variableName] == null;
    }
    if (isNull && isNonNullType(argType)) {
      throw new GraphQLError('Argument "'.concat(name, '" of non-null type "').concat(inspect(argType), '" ') + "must not be null.", valueNode);
    }
    var coercedValue = valueFromAST(valueNode, argType, variableValues);
    if (coercedValue === void 0) {
      throw new GraphQLError('Argument "'.concat(name, '" has invalid value ').concat(print(valueNode), "."), valueNode);
    }
    coercedValues[name] = coercedValue;
  }
  return coercedValues;
}
function getDirectiveValues(directiveDef, node, variableValues) {
  var directiveNode = node.directives && find_default(node.directives, function(directive) {
    return directive.name.value === directiveDef.name;
  });
  if (directiveNode) {
    return getArgumentValues(directiveDef, directiveNode, variableValues);
  }
}
function hasOwnProperty(obj, prop) {
  return Object.prototype.hasOwnProperty.call(obj, prop);
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/execution/execute.mjs
function collectFields(exeContext, runtimeType, selectionSet, fields7, visitedFragmentNames) {
  for (var _i6 = 0, _selectionSet$selecti2 = selectionSet.selections; _i6 < _selectionSet$selecti2.length; _i6++) {
    var selection = _selectionSet$selecti2[_i6];
    switch (selection.kind) {
      case Kind.FIELD: {
        if (!shouldIncludeNode(exeContext, selection)) {
          continue;
        }
        var name = getFieldEntryKey(selection);
        if (!fields7[name]) {
          fields7[name] = [];
        }
        fields7[name].push(selection);
        break;
      }
      case Kind.INLINE_FRAGMENT: {
        if (!shouldIncludeNode(exeContext, selection) || !doesFragmentConditionMatch(exeContext, selection, runtimeType)) {
          continue;
        }
        collectFields(exeContext, runtimeType, selection.selectionSet, fields7, visitedFragmentNames);
        break;
      }
      case Kind.FRAGMENT_SPREAD: {
        var fragName = selection.name.value;
        if (visitedFragmentNames[fragName] || !shouldIncludeNode(exeContext, selection)) {
          continue;
        }
        visitedFragmentNames[fragName] = true;
        var fragment = exeContext.fragments[fragName];
        if (!fragment || !doesFragmentConditionMatch(exeContext, fragment, runtimeType)) {
          continue;
        }
        collectFields(exeContext, runtimeType, fragment.selectionSet, fields7, visitedFragmentNames);
        break;
      }
    }
  }
  return fields7;
}
function shouldIncludeNode(exeContext, node) {
  var skip = getDirectiveValues(GraphQLSkipDirective, node, exeContext.variableValues);
  if ((skip === null || skip === void 0 ? void 0 : skip.if) === true) {
    return false;
  }
  var include = getDirectiveValues(GraphQLIncludeDirective, node, exeContext.variableValues);
  if ((include === null || include === void 0 ? void 0 : include.if) === false) {
    return false;
  }
  return true;
}
function doesFragmentConditionMatch(exeContext, fragment, type) {
  var typeConditionNode = fragment.typeCondition;
  if (!typeConditionNode) {
    return true;
  }
  var conditionalType = typeFromAST(exeContext.schema, typeConditionNode);
  if (conditionalType === type) {
    return true;
  }
  if (isAbstractType(conditionalType)) {
    return exeContext.schema.isSubType(conditionalType, type);
  }
  return false;
}
function getFieldEntryKey(node) {
  return node.alias ? node.alias.value : node.name.value;
}
var collectSubfields = memoize3(_collectSubfields);
function _collectSubfields(exeContext, returnType, fieldNodes) {
  var subFieldNodes = /* @__PURE__ */ Object.create(null);
  var visitedFragmentNames = /* @__PURE__ */ Object.create(null);
  for (var _i8 = 0; _i8 < fieldNodes.length; _i8++) {
    var node = fieldNodes[_i8];
    if (node.selectionSet) {
      subFieldNodes = collectFields(exeContext, returnType, node.selectionSet, subFieldNodes, visitedFragmentNames);
    }
  }
  return subFieldNodes;
}

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/extendSchema.mjs
var stdTypeMap = keyMap(specifiedScalarTypes.concat(introspectionTypes), function(type) {
  return type.name;
});

// node_modules/@aws-amplify/api-graphql/node_modules/graphql/utilities/findBreakingChanges.mjs
var BreakingChangeType = Object.freeze({
  TYPE_REMOVED: "TYPE_REMOVED",
  TYPE_CHANGED_KIND: "TYPE_CHANGED_KIND",
  TYPE_REMOVED_FROM_UNION: "TYPE_REMOVED_FROM_UNION",
  VALUE_REMOVED_FROM_ENUM: "VALUE_REMOVED_FROM_ENUM",
  REQUIRED_INPUT_FIELD_ADDED: "REQUIRED_INPUT_FIELD_ADDED",
  IMPLEMENTED_INTERFACE_REMOVED: "IMPLEMENTED_INTERFACE_REMOVED",
  FIELD_REMOVED: "FIELD_REMOVED",
  FIELD_CHANGED_KIND: "FIELD_CHANGED_KIND",
  REQUIRED_ARG_ADDED: "REQUIRED_ARG_ADDED",
  ARG_REMOVED: "ARG_REMOVED",
  ARG_CHANGED_KIND: "ARG_CHANGED_KIND",
  DIRECTIVE_REMOVED: "DIRECTIVE_REMOVED",
  DIRECTIVE_ARG_REMOVED: "DIRECTIVE_ARG_REMOVED",
  REQUIRED_DIRECTIVE_ARG_ADDED: "REQUIRED_DIRECTIVE_ARG_ADDED",
  DIRECTIVE_REPEATABLE_REMOVED: "DIRECTIVE_REPEATABLE_REMOVED",
  DIRECTIVE_LOCATION_REMOVED: "DIRECTIVE_LOCATION_REMOVED"
});
var DangerousChangeType = Object.freeze({
  VALUE_ADDED_TO_ENUM: "VALUE_ADDED_TO_ENUM",
  TYPE_ADDED_TO_UNION: "TYPE_ADDED_TO_UNION",
  OPTIONAL_INPUT_FIELD_ADDED: "OPTIONAL_INPUT_FIELD_ADDED",
  OPTIONAL_ARG_ADDED: "OPTIONAL_ARG_ADDED",
  IMPLEMENTED_INTERFACE_ADDED: "IMPLEMENTED_INTERFACE_ADDED",
  ARG_DEFAULT_VALUE_CHANGE: "ARG_DEFAULT_VALUE_CHANGE"
});

// node_modules/@aws-amplify/api-rest/dist/esm/errors/RestApiError.mjs
var RestApiError = class _RestApiError extends ApiError {
  constructor(params) {
    super(params);
    this.constructor = _RestApiError;
    Object.setPrototypeOf(this, _RestApiError.prototype);
  }
};

// node_modules/@aws-amplify/api-rest/dist/esm/errors/CanceledError.mjs
var CanceledError = class _CanceledError extends RestApiError {
  constructor(params = {}) {
    super({
      name: "CanceledError",
      message: "Request is canceled by user",
      ...params
    });
    this.constructor = _CanceledError;
    Object.setPrototypeOf(this, _CanceledError.prototype);
  }
};
var isCancelError = (error) => !!error && error instanceof CanceledError;

// node_modules/@aws-amplify/api-rest/dist/esm/errors/validation.mjs
var RestApiValidationErrorCode;
(function(RestApiValidationErrorCode2) {
  RestApiValidationErrorCode2["InvalidApiName"] = "InvalidApiName";
})(RestApiValidationErrorCode || (RestApiValidationErrorCode = {}));
var validationErrorMap = {
  [RestApiValidationErrorCode.InvalidApiName]: {
    message: "API name is invalid.",
    recoverySuggestion: "Check if the API name matches the one in your configuration or `aws-exports.js`"
  }
};

// node_modules/@aws-amplify/api-rest/dist/esm/utils/serviceError.mjs
var parseRestApiServiceError = async (response) => {
  var _a;
  if (!response) {
    return;
  }
  const parsedAwsError = await parseJsonError(stubErrorResponse(response));
  if (!parsedAwsError) ;
  else {
    const bodyText = await ((_a = response.body) == null ? void 0 : _a.text());
    return buildRestApiError(parsedAwsError, {
      statusCode: response.statusCode,
      headers: response.headers,
      body: bodyText
    });
  }
};
var stubErrorResponse = (response) => {
  let bodyTextPromise;
  const bodyProxy = new Proxy(response.body, {
    get(target, prop, receiver) {
      if (prop === "json") {
        return async () => {
          if (!bodyTextPromise) {
            bodyTextPromise = target.text();
          }
          try {
            return JSON.parse(await bodyTextPromise);
          } catch (error) {
            return {};
          }
        };
      } else if (prop === "text") {
        return async () => {
          if (!bodyTextPromise) {
            bodyTextPromise = target.text();
          }
          return bodyTextPromise;
        };
      } else {
        return Reflect.get(target, prop, receiver);
      }
    }
  });
  const responseProxy = new Proxy(response, {
    get(target, prop, receiver) {
      if (prop === "body") {
        return bodyProxy;
      } else {
        return Reflect.get(target, prop, receiver);
      }
    }
  });
  return responseProxy;
};
var buildRestApiError = (error, response) => {
  const restApiError = new RestApiError({
    name: error == null ? void 0 : error.name,
    message: error.message,
    underlyingError: error,
    response
  });
  return Object.assign(restApiError, { $metadata: error.$metadata });
};

// node_modules/@aws-amplify/api-rest/dist/esm/utils/logger.mjs
var logger = new ConsoleLogger("RestApis");

// node_modules/@aws-amplify/api-rest/dist/esm/utils/createCancellableOperation.mjs
function createCancellableOperation(handler, abortController, operationType, timeout) {
  const abortSignal = abortController.signal;
  let abortReason;
  if (timeout != null) {
    if (timeout < 0) {
      throw new Error("Timeout must be a non-negative number");
    }
    setTimeout(() => {
      abortReason = "TimeoutError";
      abortController.abort(abortReason);
    }, timeout);
  }
  const job = async () => {
    try {
      const response = await handler();
      if (response.statusCode >= 300) {
        throw await parseRestApiServiceError(response);
      }
      return response;
    } catch (error) {
      if (error.name === "AbortError" || (abortSignal == null ? void 0 : abortSignal.aborted) === true) {
        const isTimeout = abortReason && abortReason === "TimeoutError";
        if (isTimeout) {
          const timeoutError = new Error(`Request timeout after ${timeout}ms`);
          timeoutError.name = "TimeoutError";
          logger.debug(timeoutError);
          throw timeoutError;
        } else {
          const message = abortReason ?? abortSignal.reason;
          const canceledError = new CanceledError({
            ...message && { message },
            underlyingError: error,
            recoverySuggestion: "The API request was explicitly canceled. If this is not intended, validate if you called the `cancel()` function on the API request erroneously."
          });
          logger.debug(canceledError);
          throw canceledError;
        }
      }
      logger.debug(error);
      throw error;
    }
  };
  if (operationType === "internal") {
    return job();
  } else {
    const cancel3 = (abortMessage) => {
      if (abortSignal.aborted === true) {
        return;
      }
      abortController.abort(abortMessage);
      if (abortMessage && abortSignal.reason !== abortMessage) {
        abortReason = abortMessage;
      }
    };
    return { response: job(), cancel: cancel3 };
  }
}

// node_modules/@aws-amplify/api-rest/dist/esm/utils/constants.mjs
var DEFAULT_REST_IAM_SIGNING_SERVICE = "execute-api";
var DEFAULT_IAM_SIGNING_REGION = "us-east-1";
var APIG_HOSTNAME_PATTERN = /^.+\.([a-z0-9-]+)\.([a-z0-9-]+)\.amazonaws\.com/;

// node_modules/@aws-amplify/api-rest/dist/esm/utils/parseSigningInfo.mjs
var parseSigningInfo = (url, restApiOptions) => {
  var _a, _b, _c;
  const { service: signingService = DEFAULT_REST_IAM_SIGNING_SERVICE, region: signingRegion = DEFAULT_IAM_SIGNING_REGION } = ((_c = (_b = (_a = restApiOptions == null ? void 0 : restApiOptions.amplify.getConfig()) == null ? void 0 : _a.API) == null ? void 0 : _b.REST) == null ? void 0 : _c[restApiOptions == null ? void 0 : restApiOptions.apiName]) ?? {};
  const { hostname } = url;
  const [, service, region] = APIG_HOSTNAME_PATTERN.exec(hostname) ?? [];
  if (service === DEFAULT_REST_IAM_SIGNING_SERVICE) {
    return {
      service,
      region: region ?? signingRegion
    };
  } else if (service === "appsync-api") {
    return {
      service: "appsync",
      region: region ?? signingRegion
    };
  } else {
    return {
      service: signingService,
      region: signingRegion
    };
  }
};

// node_modules/@aws-amplify/api-rest/dist/esm/errors/assertValidatonError.mjs
function assertValidationError(assertion, name) {
  const { message, recoverySuggestion } = validationErrorMap[name];
  if (!assertion) {
    throw new RestApiError({ name, message, recoverySuggestion });
  }
}

// node_modules/@aws-amplify/api-rest/dist/esm/utils/resolveApiUrl.mjs
var resolveApiUrl = (amplify, apiName, path, queryParams) => {
  var _a, _b, _c, _d;
  const urlStr = (_d = (_c = (_b = (_a = amplify.getConfig()) == null ? void 0 : _a.API) == null ? void 0 : _b.REST) == null ? void 0 : _c[apiName]) == null ? void 0 : _d.endpoint;
  assertValidationError(!!urlStr, RestApiValidationErrorCode.InvalidApiName);
  try {
    let url;
    if (AmplifyUrl.canParse(urlStr + path)) {
      url = new AmplifyUrl(urlStr + path);
    } else {
      url = new AmplifyUrl(urlStr + path, location == null ? void 0 : location.origin);
    }
    if (queryParams) {
      const mergedQueryParams = new AmplifyUrlSearchParams(url.searchParams);
      Object.entries(queryParams).forEach(([key, value]) => {
        mergedQueryParams.set(key, value);
      });
      url.search = new AmplifyUrlSearchParams(mergedQueryParams).toString();
    }
    return url;
  } catch (error) {
    throw new RestApiError({
      name: RestApiValidationErrorCode.InvalidApiName,
      ...validationErrorMap[RestApiValidationErrorCode.InvalidApiName],
      recoverySuggestion: `Please make sure the REST endpoint URL is a valid URL string. Got ${urlStr}`
    });
  }
};

// node_modules/@aws-amplify/api-rest/dist/esm/utils/isIamAuthApplicable.mjs
var isIamAuthApplicableForGraphQL = ({ headers }, signingServiceInfo) => !headers.authorization && !headers["x-api-key"] && !!signingServiceInfo;
var isIamAuthApplicableForRest = ({ headers }, signingServiceInfo) => !headers.authorization && !!signingServiceInfo;

// node_modules/@aws-amplify/api-rest/dist/esm/utils/resolveLibraryOptions.mjs
var resolveLibraryOptions = (amplify) => {
  var _a, _b, _c, _d, _e, _f;
  const retryStrategy = (_c = (_b = (_a = amplify.libraryOptions) == null ? void 0 : _a.API) == null ? void 0 : _b.REST) == null ? void 0 : _c.retryStrategy;
  const defaultAuthMode = (_f = (_e = (_d = amplify.libraryOptions) == null ? void 0 : _d.API) == null ? void 0 : _e.REST) == null ? void 0 : _f.defaultAuthMode;
  return { retryStrategy, defaultAuthMode };
};

// node_modules/@aws-amplify/api-rest/dist/esm/utils/resolveHeaders.mjs
var resolveHeaders = (headers, body) => {
  const normalizedHeaders = {};
  for (const key in headers) {
    normalizedHeaders[key.toLowerCase()] = headers[key];
  }
  if (body) {
    const contentType = normalizedHeaders["content-type"];
    const isJsonCompatible = contentType && (contentType.startsWith("application/json") || contentType.startsWith("application/") && contentType.includes("+json"));
    if (!isJsonCompatible) {
      normalizedHeaders["content-type"] = "application/json; charset=UTF-8";
    }
    if (body instanceof FormData) {
      delete normalizedHeaders["content-type"];
    }
  }
  return normalizedHeaders;
};

// node_modules/@aws-amplify/api-rest/dist/esm/apis/common/baseHandlers/authenticatedHandler.mjs
var authenticatedHandler = composeTransferHandler(fetchTransferHandler, [
  userAgentMiddlewareFactory,
  retryMiddlewareFactory,
  signingMiddlewareFactory
]);

// node_modules/@aws-amplify/api-rest/dist/esm/apis/common/baseHandlers/unauthenticatedHandler.mjs
var unauthenticatedHandler = composeTransferHandler(fetchTransferHandler, [userAgentMiddlewareFactory, retryMiddlewareFactory]);

// node_modules/@aws-amplify/api-rest/dist/esm/apis/common/transferHandler.mjs
var transferHandler = async (amplify, options, iamAuthApplicable, signingServiceInfo) => {
  const { url, method, headers, body, withCredentials, abortSignal, retryStrategy } = options;
  const resolvedBody = body ? body instanceof FormData ? body : JSON.stringify(body ?? "") : void 0;
  const resolvedHeaders = resolveHeaders(headers, body);
  const request = {
    url,
    headers: resolvedHeaders,
    method,
    body: resolvedBody
  };
  const { retryStrategy: libraryRetryStrategy, defaultAuthMode: libraryDefaultAuthMode } = resolveLibraryOptions(amplify);
  const baseOptions = {
    retryDecider: getRetryDeciderFromStrategy(retryStrategy ?? libraryRetryStrategy),
    computeDelay: jitteredBackoff,
    withCrossDomainCredentials: withCredentials,
    abortSignal
  };
  const defaultAuthMode = options.defaultAuthMode ?? libraryDefaultAuthMode;
  let credentials = null;
  if (defaultAuthMode !== "none") {
    credentials = await resolveCredentials(amplify);
  }
  let response;
  const isIamAuthApplicable = iamAuthApplicable(request, signingServiceInfo);
  if (isIamAuthApplicable && credentials) {
    const signingInfoFromUrl = parseSigningInfo(url);
    const signingService = (signingServiceInfo == null ? void 0 : signingServiceInfo.service) ?? signingInfoFromUrl.service;
    const signingRegion = (signingServiceInfo == null ? void 0 : signingServiceInfo.region) ?? signingInfoFromUrl.region;
    response = await authenticatedHandler(request, {
      ...baseOptions,
      credentials,
      region: signingRegion,
      service: signingService
    });
  } else {
    response = await unauthenticatedHandler(request, {
      ...baseOptions
    });
  }
  return {
    statusCode: response.statusCode,
    headers: response.headers,
    body: response.body
  };
};
var getRetryDeciderFromStrategy = (retryStrategy) => {
  const strategy = retryStrategy == null ? void 0 : retryStrategy.strategy;
  if (strategy === "no-retry") {
    return () => Promise.resolve({ retryable: false });
  }
  return getRetryDecider(parseRestApiServiceError);
};
var resolveCredentials = async (amplify) => {
  try {
    const { credentials } = await amplify.Auth.fetchAuthSession();
    if (credentials) {
      return credentials;
    }
  } catch (e) {
    logger.debug("No credentials available, the request will be unsigned.");
  }
  return null;
};

// node_modules/@aws-amplify/api-rest/dist/esm/apis/common/publicApis.mjs
var publicHandler = (amplify, options, method) => {
  var _a, _b, _c, _d;
  const { apiName, options: apiOptions = {}, path: apiPath } = options;
  const libraryConfigTimeout = (_d = (_c = (_b = (_a = amplify.libraryOptions) == null ? void 0 : _a.API) == null ? void 0 : _b.REST) == null ? void 0 : _c.timeout) == null ? void 0 : _d.call(_c, {
    apiName,
    method
  });
  const timeout = (apiOptions == null ? void 0 : apiOptions.timeout) || libraryConfigTimeout || void 0;
  const publicApisAbortController = new AbortController();
  const abortSignal = publicApisAbortController.signal;
  return createCancellableOperation(
    async () => {
      var _a2, _b2, _c2, _d2;
      const url = resolveApiUrl(amplify, apiName, apiPath, apiOptions == null ? void 0 : apiOptions.queryParams);
      const libraryConfigHeaders = await ((_d2 = (_c2 = (_b2 = (_a2 = amplify.libraryOptions) == null ? void 0 : _a2.API) == null ? void 0 : _b2.REST) == null ? void 0 : _c2.headers) == null ? void 0 : _d2.call(_c2, {
        apiName
      }));
      const { headers: invocationHeaders = {} } = apiOptions;
      const headers = {
        // custom headers from invocation options should precede library options
        ...libraryConfigHeaders,
        ...invocationHeaders
      };
      const signingServiceInfo = parseSigningInfo(url, {
        amplify,
        apiName
      });
      logger.debug(method, url, headers, `IAM signing options: ${JSON.stringify(signingServiceInfo)}`);
      return transferHandler(amplify, {
        ...apiOptions,
        url,
        method,
        headers,
        abortSignal
      }, isIamAuthApplicableForRest, signingServiceInfo);
    },
    publicApisAbortController,
    "public",
    // operation Type
    timeout
  );
};
var get3 = (amplify, input) => publicHandler(amplify, input, "GET");
var post = (amplify, input) => publicHandler(amplify, input, "POST");
var put = (amplify, input) => publicHandler(amplify, input, "PUT");
var del = (amplify, input) => publicHandler(amplify, input, "DELETE");
var head = (amplify, input) => publicHandler(amplify, input, "HEAD");
var patch = (amplify, input) => publicHandler(amplify, input, "PATCH");

// node_modules/@aws-amplify/api-rest/dist/esm/apis/index.mjs
var get4 = (input) => get3(Amplify, input);
var post2 = (input) => post(Amplify, input);
var put2 = (input) => put(Amplify, input);
var del2 = (input) => del(Amplify, input);
var head2 = (input) => head(Amplify, input);
var patch2 = (input) => patch(Amplify, input);

// node_modules/@aws-amplify/api-rest/dist/esm/apis/common/internalPost.mjs
var cancelTokenMap = /* @__PURE__ */ new WeakMap();
var post3 = (amplify, { url, options, abortController }) => {
  const controller = abortController ?? new AbortController();
  const responsePromise = createCancellableOperation(async () => {
    const response = transferHandler(amplify, {
      url,
      method: "POST",
      ...options,
      abortSignal: controller.signal,
      retryStrategy: {
        strategy: "jittered-exponential-backoff"
      }
    }, isIamAuthApplicableForGraphQL, options == null ? void 0 : options.signingServiceInfo);
    return response;
  }, controller, "internal");
  const responseWithCleanUp = responsePromise.finally(() => {
    cancelTokenMap.delete(responseWithCleanUp);
  });
  return responseWithCleanUp;
};
var cancel = (promise, message) => {
  const controller = cancelTokenMap.get(promise);
  if (controller) {
    controller.abort(message);
    if (message && controller.signal.reason !== message) {
      controller.signal.reason = message;
    }
    return true;
  }
  return false;
};
var updateRequestToBeCancellable = (promise, controller) => {
  cancelTokenMap.set(promise, controller);
};

// node_modules/@aws-amplify/api-graphql/dist/esm/Providers/constants.mjs
var MAX_DELAY_MS = 5e3;
var NON_RETRYABLE_CODES = [400, 401, 403];
var NON_RETRYABLE_ERROR_TYPES = [
  "BadRequestException",
  "UnauthorizedException"
];
var CONNECTION_STATE_CHANGE = "ConnectionStateChange";
var MESSAGE_TYPES;
(function(MESSAGE_TYPES2) {
  MESSAGE_TYPES2["GQL_CONNECTION_INIT"] = "connection_init";
  MESSAGE_TYPES2["GQL_CONNECTION_ERROR"] = "connection_error";
  MESSAGE_TYPES2["GQL_CONNECTION_ACK"] = "connection_ack";
  MESSAGE_TYPES2["GQL_START"] = "start";
  MESSAGE_TYPES2["GQL_START_ACK"] = "start_ack";
  MESSAGE_TYPES2["DATA"] = "data";
  MESSAGE_TYPES2["GQL_CONNECTION_KEEP_ALIVE"] = "ka";
  MESSAGE_TYPES2["GQL_STOP"] = "stop";
  MESSAGE_TYPES2["GQL_COMPLETE"] = "complete";
  MESSAGE_TYPES2["GQL_ERROR"] = "error";
  MESSAGE_TYPES2["EVENT_SUBSCRIBE"] = "subscribe";
  MESSAGE_TYPES2["EVENT_PUBLISH"] = "publish";
  MESSAGE_TYPES2["EVENT_SUBSCRIBE_ACK"] = "subscribe_success";
  MESSAGE_TYPES2["EVENT_PUBLISH_ACK"] = "publish_success";
  MESSAGE_TYPES2["EVENT_STOP"] = "unsubscribe";
  MESSAGE_TYPES2["EVENT_COMPLETE"] = "unsubscribe_success";
  MESSAGE_TYPES2["EVENT_SUBSCRIBE_ERROR"] = "subscribe_error";
})(MESSAGE_TYPES || (MESSAGE_TYPES = {}));
var SUBSCRIPTION_STATUS;
(function(SUBSCRIPTION_STATUS2) {
  SUBSCRIPTION_STATUS2[SUBSCRIPTION_STATUS2["PENDING"] = 0] = "PENDING";
  SUBSCRIPTION_STATUS2[SUBSCRIPTION_STATUS2["CONNECTED"] = 1] = "CONNECTED";
  SUBSCRIPTION_STATUS2[SUBSCRIPTION_STATUS2["FAILED"] = 2] = "FAILED";
})(SUBSCRIPTION_STATUS || (SUBSCRIPTION_STATUS = {}));
var SOCKET_STATUS;
(function(SOCKET_STATUS2) {
  SOCKET_STATUS2[SOCKET_STATUS2["CLOSED"] = 0] = "CLOSED";
  SOCKET_STATUS2[SOCKET_STATUS2["READY"] = 1] = "READY";
  SOCKET_STATUS2[SOCKET_STATUS2["CONNECTING"] = 2] = "CONNECTING";
})(SOCKET_STATUS || (SOCKET_STATUS = {}));
var AWS_APPSYNC_REALTIME_HEADERS = {
  accept: "application/json, text/javascript",
  "content-encoding": "amz-1.0",
  "content-type": "application/json; charset=UTF-8"
};
var CONNECTION_INIT_TIMEOUT = 15e3;
var START_ACK_TIMEOUT = 15e3;
var DEFAULT_KEEP_ALIVE_TIMEOUT = 5 * 60 * 1e3;
var DEFAULT_KEEP_ALIVE_HEARTBEAT_TIMEOUT = 5 * 1e3;
var DEFAULT_KEEP_ALIVE_ALERT_TIMEOUT = 65 * 1e3;
var RECONNECT_DELAY = 5 * 1e3;
var RECONNECT_INTERVAL = 60 * 1e3;

// node_modules/@aws-amplify/api-graphql/dist/esm/types/PubSub.mjs
var CONTROL_MSG;
(function(CONTROL_MSG2) {
  CONTROL_MSG2["CONNECTION_CLOSED"] = "Connection closed";
  CONTROL_MSG2["CONNECTION_FAILED"] = "Connection failed";
  CONTROL_MSG2["REALTIME_SUBSCRIPTION_INIT_ERROR"] = "AppSync Realtime subscription init error";
  CONTROL_MSG2["SUBSCRIPTION_ACK"] = "Subscription ack";
  CONTROL_MSG2["TIMEOUT_DISCONNECT"] = "Timeout disconnect";
})(CONTROL_MSG || (CONTROL_MSG = {}));
var ConnectionState;
(function(ConnectionState2) {
  ConnectionState2["Connected"] = "Connected";
  ConnectionState2["ConnectedPendingNetwork"] = "ConnectedPendingNetwork";
  ConnectionState2["ConnectionDisrupted"] = "ConnectionDisrupted";
  ConnectionState2["ConnectionDisruptedPendingNetwork"] = "ConnectionDisruptedPendingNetwork";
  ConnectionState2["Connecting"] = "Connecting";
  ConnectionState2["ConnectedPendingDisconnect"] = "ConnectedPendingDisconnect";
  ConnectionState2["Disconnected"] = "Disconnected";
  ConnectionState2["ConnectedPendingKeepAlive"] = "ConnectedPendingKeepAlive";
})(ConnectionState || (ConnectionState = {}));

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/ReachabilityMonitor/index.mjs
var ReachabilityMonitor = () => new Reachability().networkMonitor();

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/ConnectionStateMonitor.mjs
var CONNECTION_CHANGE = {
  KEEP_ALIVE_MISSED: { keepAliveState: "unhealthy" },
  KEEP_ALIVE: { keepAliveState: "healthy" },
  CONNECTION_ESTABLISHED: { connectionState: "connected" },
  CONNECTION_FAILED: {
    intendedConnectionState: "disconnected",
    connectionState: "disconnected"
  },
  CLOSING_CONNECTION: { intendedConnectionState: "disconnected" },
  OPENING_CONNECTION: {
    intendedConnectionState: "connected",
    connectionState: "connecting"
  },
  CLOSED: { connectionState: "disconnected" },
  ONLINE: { networkState: "connected" },
  OFFLINE: { networkState: "disconnected" }
};
var ConnectionStateMonitor = class {
  constructor() {
    this._networkMonitoringSubscription = void 0;
    this._linkedConnectionState = {
      networkState: "connected",
      connectionState: "disconnected",
      intendedConnectionState: "disconnected",
      keepAliveState: "healthy"
    };
    this._initialNetworkStateSubscription = ReachabilityMonitor().subscribe(({ online }) => {
      var _a;
      this.record(online ? CONNECTION_CHANGE.ONLINE : CONNECTION_CHANGE.OFFLINE);
      (_a = this._initialNetworkStateSubscription) == null ? void 0 : _a.unsubscribe();
    });
    this._linkedConnectionStateObservable = new Observable((connectionStateObserver) => {
      connectionStateObserver.next(this._linkedConnectionState);
      this._linkedConnectionStateObserver = connectionStateObserver;
    });
  }
  /**
   * Turn network state monitoring on if it isn't on already
   */
  enableNetworkMonitoring() {
    var _a;
    (_a = this._initialNetworkStateSubscription) == null ? void 0 : _a.unsubscribe();
    if (this._networkMonitoringSubscription === void 0) {
      this._networkMonitoringSubscription = ReachabilityMonitor().subscribe(({ online }) => {
        this.record(online ? CONNECTION_CHANGE.ONLINE : CONNECTION_CHANGE.OFFLINE);
      });
    }
  }
  /**
   * Turn network state monitoring off if it isn't off already
   */
  disableNetworkMonitoring() {
    var _a;
    (_a = this._networkMonitoringSubscription) == null ? void 0 : _a.unsubscribe();
    this._networkMonitoringSubscription = void 0;
  }
  /**
   * Get the observable that allows us to monitor the connection state
   *
   * @returns {Observable<ConnectionState>} - The observable that emits ConnectionState updates
   */
  get connectionStateObservable() {
    let previous;
    return this._linkedConnectionStateObservable.pipe(map((value) => {
      return this.connectionStatesTranslator(value);
    })).pipe(filter((current) => {
      const toInclude = current !== previous;
      previous = current;
      return toInclude;
    }));
  }
  /*
   * Updates local connection state and emits the full state to the observer.
   */
  record(statusUpdates) {
    var _a;
    if (statusUpdates.intendedConnectionState === "connected") {
      this.enableNetworkMonitoring();
    } else if (statusUpdates.intendedConnectionState === "disconnected") {
      this.disableNetworkMonitoring();
    }
    const newSocketStatus = {
      ...this._linkedConnectionState,
      ...statusUpdates
    };
    this._linkedConnectionState = { ...newSocketStatus };
    (_a = this._linkedConnectionStateObserver) == null ? void 0 : _a.next(this._linkedConnectionState);
  }
  /*
   * Translate the ConnectionState structure into a specific ConnectionState string literal union
   */
  connectionStatesTranslator({ connectionState, networkState, intendedConnectionState, keepAliveState }) {
    if (connectionState === "connected" && networkState === "disconnected")
      return ConnectionState.ConnectedPendingNetwork;
    if (connectionState === "connected" && intendedConnectionState === "disconnected")
      return ConnectionState.ConnectedPendingDisconnect;
    if (connectionState === "disconnected" && intendedConnectionState === "connected" && networkState === "disconnected")
      return ConnectionState.ConnectionDisruptedPendingNetwork;
    if (connectionState === "disconnected" && intendedConnectionState === "connected")
      return ConnectionState.ConnectionDisrupted;
    if (connectionState === "connected" && keepAliveState === "unhealthy")
      return ConnectionState.ConnectedPendingKeepAlive;
    if (connectionState === "connecting")
      return ConnectionState.Connecting;
    if (connectionState === "disconnected")
      return ConnectionState.Disconnected;
    return ConnectionState.Connected;
  }
};

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/ReconnectionMonitor.mjs
var ReconnectEvent;
(function(ReconnectEvent2) {
  ReconnectEvent2["START_RECONNECT"] = "START_RECONNECT";
  ReconnectEvent2["HALT_RECONNECT"] = "HALT_RECONNECT";
})(ReconnectEvent || (ReconnectEvent = {}));
var ReconnectionMonitor = class {
  constructor() {
    this.reconnectObservers = [];
  }
  /**
   * Add reconnect observer to the list of observers to alert on reconnect
   */
  addObserver(reconnectObserver) {
    this.reconnectObservers.push(reconnectObserver);
  }
  /**
   * Given a reconnect event, start the appropriate behavior
   */
  record(event) {
    if (event === ReconnectEvent.START_RECONNECT) {
      if (this.reconnectSetTimeoutId === void 0 && this.reconnectIntervalId === void 0) {
        this.reconnectSetTimeoutId = setTimeout(() => {
          this._triggerReconnect();
          this.reconnectIntervalId = setInterval(() => {
            this._triggerReconnect();
          }, RECONNECT_INTERVAL);
        }, RECONNECT_DELAY);
      }
    }
    if (event === ReconnectEvent.HALT_RECONNECT) {
      if (this.reconnectIntervalId) {
        clearInterval(this.reconnectIntervalId);
        this.reconnectIntervalId = void 0;
      }
      if (this.reconnectSetTimeoutId) {
        clearTimeout(this.reconnectSetTimeoutId);
        this.reconnectSetTimeoutId = void 0;
      }
    }
  }
  /**
   * Complete all reconnect observers
   */
  close() {
    this.reconnectObservers.forEach((reconnectObserver) => {
      var _a;
      (_a = reconnectObserver.complete) == null ? void 0 : _a.call(reconnectObserver);
    });
  }
  _triggerReconnect() {
    this.reconnectObservers.forEach((reconnectObserver) => {
      var _a;
      (_a = reconnectObserver.next) == null ? void 0 : _a.call(reconnectObserver);
    });
  }
};

// node_modules/@aws-amplify/api-graphql/dist/esm/Providers/AWSWebSocketProvider/appsyncUrl.mjs
var protocol = "wss://";
var standardDomainPattern = /^https:\/\/\w{26}\.appsync-api\.\w{2}(?:(?:-\w{2,})+)-\d\.amazonaws.com(?:\.cn)?\/graphql$/i;
var eventDomainPattern = /^https:\/\/\w{26}\.\w+-api\.\w{2}(?:(?:-\w{2,})+)-\d\.amazonaws.com(?:\.cn)?\/event$/i;
var customDomainPath = "/realtime";
var isCustomDomain = (url) => {
  return url.match(standardDomainPattern) === null;
};
var isEventDomain = (url) => url.match(eventDomainPattern) !== null;
var getRealtimeEndpointUrl = (appSyncGraphqlEndpoint) => {
  let realtimeEndpoint = appSyncGraphqlEndpoint ?? "";
  if (isEventDomain(realtimeEndpoint)) {
    realtimeEndpoint = realtimeEndpoint.concat(customDomainPath).replace("ddpg-api", "grt-gamma").replace("appsync-api", "appsync-realtime-api");
  } else if (isCustomDomain(realtimeEndpoint)) {
    realtimeEndpoint = realtimeEndpoint.concat(customDomainPath);
  } else {
    realtimeEndpoint = realtimeEndpoint.replace("appsync-api", "appsync-realtime-api").replace("gogi-beta", "grt-beta").replace("ddpg-api", "grt-gamma");
  }
  realtimeEndpoint = realtimeEndpoint.replace("https://", protocol).replace("http://", protocol);
  return new AmplifyUrl(realtimeEndpoint);
};
var extractNonAuthHeaders = (headers) => {
  if (!headers) {
    return {};
  }
  if ("Authorization" in headers) {
    const { Authorization: _, ...nonAuthHeaders } = headers;
    return nonAuthHeaders;
  }
  return headers;
};
var queryParamsFromCustomHeaders = (headers) => {
  const nonAuthHeaders = extractNonAuthHeaders(headers);
  const params = new AmplifyUrlSearchParams();
  Object.entries(nonAuthHeaders).forEach(([k, v]) => {
    params.append(k, v);
  });
  return params;
};
var realtimeUrlWithQueryString = (appSyncGraphqlEndpoint, urlParams) => {
  const realtimeEndpointUrl = getRealtimeEndpointUrl(appSyncGraphqlEndpoint);
  const existingParams = new AmplifyUrlSearchParams(realtimeEndpointUrl.search);
  for (const [k, v] of urlParams.entries()) {
    existingParams.append(k, v);
  }
  realtimeEndpointUrl.search = existingParams.toString();
  return realtimeEndpointUrl.toString();
};
var additionalHeadersFromOptions = async (options) => {
  const { appSyncGraphqlEndpoint, query, libraryConfigHeaders = () => ({}), additionalHeaders = {}, authToken } = options;
  let additionalCustomHeaders = {};
  const _libraryConfigHeaders = await libraryConfigHeaders();
  if (typeof additionalHeaders === "function") {
    const requestOptions = {
      url: appSyncGraphqlEndpoint || "",
      queryString: query || ""
    };
    additionalCustomHeaders = await additionalHeaders(requestOptions);
  } else {
    additionalCustomHeaders = additionalHeaders;
  }
  if (authToken) {
    additionalCustomHeaders = {
      ...additionalCustomHeaders,
      Authorization: authToken
    };
  }
  return {
    additionalCustomHeaders,
    libraryConfigHeaders: _libraryConfigHeaders
  };
};

// node_modules/@aws-amplify/api-graphql/dist/esm/Providers/AWSWebSocketProvider/authHeaders.mjs
var logger2 = new ConsoleLogger("AWSAppSyncRealTimeProvider Auth");
var awsAuthTokenHeader = async ({ host }) => {
  var _a, _b;
  const session = await fetchAuthSession();
  return {
    Authorization: (_b = (_a = session == null ? void 0 : session.tokens) == null ? void 0 : _a.accessToken) == null ? void 0 : _b.toString(),
    host
  };
};
var awsRealTimeApiKeyHeader = async ({ apiKey, host }) => {
  const dt = /* @__PURE__ */ new Date();
  const dtStr = dt.toISOString().replace(/[:-]|\.\d{3}/g, "");
  return {
    host,
    "x-amz-date": dtStr,
    "x-api-key": apiKey
  };
};
var awsRealTimeIAMHeader = async ({ payload, canonicalUri, appSyncGraphqlEndpoint, region }) => {
  const endpointInfo = {
    region,
    service: "appsync"
  };
  const creds = (await fetchAuthSession()).credentials;
  const request = {
    url: `${appSyncGraphqlEndpoint}${canonicalUri}`,
    data: payload,
    method: "POST",
    headers: { ...AWS_APPSYNC_REALTIME_HEADERS }
  };
  const signedParams = signRequest({
    headers: request.headers,
    method: request.method,
    url: new AmplifyUrl(request.url),
    body: request.data
  }, {
    credentials: creds,
    signingRegion: endpointInfo.region,
    signingService: endpointInfo.service
  });
  return signedParams.headers;
};
var customAuthHeader = async ({ host, additionalCustomHeaders }) => {
  if (!(additionalCustomHeaders == null ? void 0 : additionalCustomHeaders.Authorization)) {
    throw new Error("No auth token specified");
  }
  return {
    Authorization: additionalCustomHeaders.Authorization,
    host
  };
};
var awsRealTimeHeaderBasedAuth = async ({ apiKey, authenticationType, canonicalUri, appSyncGraphqlEndpoint, region, additionalCustomHeaders, payload }) => {
  const headerHandler = {
    apiKey: awsRealTimeApiKeyHeader,
    iam: awsRealTimeIAMHeader,
    oidc: awsAuthTokenHeader,
    userPool: awsAuthTokenHeader,
    lambda: customAuthHeader,
    none: customAuthHeader
  };
  if (!authenticationType || !headerHandler[authenticationType]) {
    logger2.debug(`Authentication type ${authenticationType} not supported`);
    return void 0;
  } else {
    const handler = headerHandler[authenticationType];
    const host = appSyncGraphqlEndpoint ? new AmplifyUrl(appSyncGraphqlEndpoint).host : void 0;
    const resolvedApiKey = authenticationType === "apiKey" ? apiKey : void 0;
    logger2.debug(`Authenticating with ${JSON.stringify(authenticationType)}`);
    const result = await handler({
      payload,
      canonicalUri,
      appSyncGraphqlEndpoint,
      apiKey: resolvedApiKey,
      region,
      host,
      additionalCustomHeaders
    });
    return result;
  }
};

// node_modules/@aws-amplify/api-graphql/dist/esm/Providers/AWSWebSocketProvider/index.mjs
var dispatchApiEvent = (payload) => {
  Hub.dispatch("api", payload, "PubSub", AMPLIFY_SYMBOL);
};
var AWSWebSocketProvider = class {
  constructor(args) {
    this.subscriptionObserverMap = /* @__PURE__ */ new Map();
    this.allowNoSubscriptions = false;
    this.socketStatus = SOCKET_STATUS.CLOSED;
    this.keepAliveTimestamp = Date.now();
    this.promiseArray = [];
    this.connectionStateMonitor = new ConnectionStateMonitor();
    this.reconnectionMonitor = new ReconnectionMonitor();
    this._establishConnection = async (awsRealTimeUrl, subprotocol) => {
      this.logger.debug(`Establishing WebSocket connection to ${awsRealTimeUrl}`);
      try {
        await this._openConnection(awsRealTimeUrl, subprotocol);
        await this._initiateHandshake();
      } catch (err) {
        const { errorType, errorCode } = err;
        if (NON_RETRYABLE_CODES.includes(errorCode) || // Event API does not currently return `errorCode`. This may change in the future.
        // For now fall back to also checking known non-retryable error types
        NON_RETRYABLE_ERROR_TYPES.includes(errorType)) {
          throw new NonRetryableError(errorType);
        } else if (errorType) {
          throw new Error(errorType);
        } else {
          throw err;
        }
      }
    };
    this.logger = new ConsoleLogger(args.providerName);
    this.wsProtocolName = args.wsProtocolName;
    this.wsConnectUri = args.connectUri;
    this.connectionStateMonitorSubscription = this._startConnectionStateMonitoring();
  }
  /**
   * Mark the socket closed and release all active listeners
   */
  close() {
    this.socketStatus = SOCKET_STATUS.CLOSED;
    this.connectionStateMonitor.record(CONNECTION_CHANGE.CONNECTION_FAILED);
    this.connectionStateMonitorSubscription.unsubscribe();
    this.reconnectionMonitor.close();
    return new Promise((resolve4, reject) => {
      if (this.awsRealTimeSocket) {
        this.awsRealTimeSocket.onclose = (_) => {
          this._closeSocket();
          this.subscriptionObserverMap = /* @__PURE__ */ new Map();
          this.awsRealTimeSocket = void 0;
          resolve4();
        };
        this.awsRealTimeSocket.onerror = (err) => {
          reject(err);
        };
        this.awsRealTimeSocket.close();
      } else {
        resolve4();
      }
    });
  }
  subscribe(options, customUserAgentDetails) {
    return new Observable((observer) => {
      if (!(options == null ? void 0 : options.appSyncGraphqlEndpoint)) {
        observer.error({
          errors: [
            {
              ...new GraphQLError(`Subscribe only available for AWS AppSync endpoint`)
            }
          ]
        });
        observer.complete();
        return;
      }
      let subscriptionStartInProgress = false;
      const subscriptionId = amplifyUuid();
      const startSubscription = () => {
        if (!subscriptionStartInProgress) {
          subscriptionStartInProgress = true;
          this._startSubscriptionWithAWSAppSyncRealTime({
            options,
            observer,
            subscriptionId,
            customUserAgentDetails
          }).catch((err) => {
            this.logger.debug(`${CONTROL_MSG.REALTIME_SUBSCRIPTION_INIT_ERROR}: ${err}`);
            this._closeSocket();
          }).finally(() => {
            subscriptionStartInProgress = false;
          });
        }
      };
      const reconnectSubscription = new Observable((reconnectSubscriptionObserver) => {
        this.reconnectionMonitor.addObserver(reconnectSubscriptionObserver);
      }).subscribe(() => {
        startSubscription();
      });
      startSubscription();
      return async () => {
        await this._cleanupSubscription(subscriptionId, reconnectSubscription);
      };
    });
  }
  async connect(options) {
    if (this.socketStatus === SOCKET_STATUS.READY) {
      return;
    }
    await this._connectWebSocket(options);
  }
  async publish(options, customUserAgentDetails) {
    if (this.socketStatus !== SOCKET_STATUS.READY) {
      throw new Error("Subscription has not been initialized");
    }
    return this._publishMessage(options, customUserAgentDetails);
  }
  async _connectWebSocket(options) {
    const { apiKey, appSyncGraphqlEndpoint, authenticationType, region } = options;
    const { additionalCustomHeaders } = await additionalHeadersFromOptions(options);
    this.connectionStateMonitor.record(CONNECTION_CHANGE.OPENING_CONNECTION);
    await this._initializeWebSocketConnection({
      apiKey,
      appSyncGraphqlEndpoint,
      authenticationType,
      region,
      additionalCustomHeaders
    });
  }
  async _publishMessage(options, customUserAgentDetails) {
    const subscriptionId = amplifyUuid();
    const { additionalCustomHeaders, libraryConfigHeaders } = await additionalHeadersFromOptions(options);
    const serializedSubscriptionMessage = await this._prepareSubscriptionPayload({
      options,
      subscriptionId,
      customUserAgentDetails,
      additionalCustomHeaders,
      libraryConfigHeaders,
      publish: true
    });
    return new Promise((resolve4, reject) => {
      if (this.awsRealTimeSocket) {
        const publishListener = (event) => {
          const data = JSON.parse(event.data);
          if (data.id === subscriptionId && data.type === "publish_success") {
            this.awsRealTimeSocket && this.awsRealTimeSocket.removeEventListener("message", publishListener);
            cleanup();
            resolve4();
          }
          if (data.errors && data.errors.length > 0) {
            const errorTypes = data.errors.map((error) => error.errorType);
            cleanup();
            reject(new Error(`Publish errors: ${errorTypes.join(", ")}`));
          }
        };
        const errorListener = (error) => {
          cleanup();
          reject(new Error(`WebSocket error: ${error}`));
        };
        const closeListener = () => {
          cleanup();
          reject(new Error("WebSocket is closed"));
        };
        const cleanup = () => {
          var _a, _b, _c;
          (_a = this.awsRealTimeSocket) == null ? void 0 : _a.removeEventListener("message", publishListener);
          (_b = this.awsRealTimeSocket) == null ? void 0 : _b.removeEventListener("error", errorListener);
          (_c = this.awsRealTimeSocket) == null ? void 0 : _c.removeEventListener("close", closeListener);
        };
        this.awsRealTimeSocket.addEventListener("message", publishListener);
        this.awsRealTimeSocket.addEventListener("error", errorListener);
        this.awsRealTimeSocket.addEventListener("close", closeListener);
        this.awsRealTimeSocket.send(serializedSubscriptionMessage);
      } else {
        reject(new Error("WebSocket is not connected"));
      }
    });
  }
  async _cleanupSubscription(subscriptionId, reconnectSubscription) {
    reconnectSubscription == null ? void 0 : reconnectSubscription.unsubscribe();
    try {
      await this._waitForSubscriptionToBeConnected(subscriptionId);
      const { subscriptionState } = this.subscriptionObserverMap.get(subscriptionId) || {};
      if (!subscriptionState) {
        return;
      }
      if (subscriptionState === SUBSCRIPTION_STATUS.CONNECTED) {
        this._sendUnsubscriptionMessage(subscriptionId);
      } else {
        throw new Error("Subscription never connected");
      }
    } catch (err) {
      this.logger.debug(`Error while unsubscribing ${err}`);
    } finally {
      this._removeSubscriptionObserver(subscriptionId);
    }
  }
  // Monitor the connection state and pass changes along to Hub
  _startConnectionStateMonitoring() {
    return this.connectionStateMonitor.connectionStateObservable.subscribe((connectionState) => {
      dispatchApiEvent({
        event: CONNECTION_STATE_CHANGE,
        data: {
          provider: this,
          connectionState
        },
        message: `Connection state is ${connectionState}`
      });
      this.connectionState = connectionState;
      if (connectionState === ConnectionState.ConnectionDisrupted) {
        this.reconnectionMonitor.record(ReconnectEvent.START_RECONNECT);
      }
      if ([
        ConnectionState.Connected,
        ConnectionState.ConnectedPendingDisconnect,
        ConnectionState.ConnectedPendingKeepAlive,
        ConnectionState.ConnectedPendingNetwork,
        ConnectionState.ConnectionDisruptedPendingNetwork,
        ConnectionState.Disconnected
      ].includes(connectionState)) {
        this.reconnectionMonitor.record(ReconnectEvent.HALT_RECONNECT);
      }
    });
  }
  async _startSubscriptionWithAWSAppSyncRealTime({ options, observer, subscriptionId, customUserAgentDetails }) {
    const { query, variables } = options;
    this.subscriptionObserverMap.set(subscriptionId, {
      observer,
      query: query ?? "",
      variables: variables ?? {},
      subscriptionState: SUBSCRIPTION_STATUS.PENDING,
      startAckTimeoutId: void 0
    });
    const { additionalCustomHeaders, libraryConfigHeaders } = await additionalHeadersFromOptions(options);
    const serializedSubscriptionMessage = await this._prepareSubscriptionPayload({
      options,
      subscriptionId,
      customUserAgentDetails,
      additionalCustomHeaders,
      libraryConfigHeaders
    });
    try {
      await this._connectWebSocket(options);
    } catch (err) {
      this._logStartSubscriptionError(subscriptionId, observer, err);
      return;
    }
    const { subscriptionFailedCallback, subscriptionReadyCallback } = this.subscriptionObserverMap.get(subscriptionId) ?? {};
    this.subscriptionObserverMap.set(subscriptionId, {
      observer,
      subscriptionState: SUBSCRIPTION_STATUS.PENDING,
      query: query ?? "",
      variables: variables ?? {},
      subscriptionReadyCallback,
      subscriptionFailedCallback,
      startAckTimeoutId: setTimeout(() => {
        this._timeoutStartSubscriptionAck(subscriptionId);
      }, START_ACK_TIMEOUT)
    });
    if (this.awsRealTimeSocket) {
      this.awsRealTimeSocket.send(serializedSubscriptionMessage);
    }
  }
  // Log logic for start subscription failures
  _logStartSubscriptionError(subscriptionId, observer, err) {
    this.logger.debug({ err });
    const message = String(err.message ?? "");
    this._closeSocket();
    if (this.connectionState !== ConnectionState.ConnectionDisruptedPendingNetwork) {
      if (isNonRetryableError(err)) {
        observer.error({
          errors: [
            {
              ...new GraphQLError(`${CONTROL_MSG.CONNECTION_FAILED}: ${message}`)
            }
          ]
        });
      } else {
        this.logger.debug(`${CONTROL_MSG.CONNECTION_FAILED}: ${message}`);
      }
      const { subscriptionFailedCallback } = this.subscriptionObserverMap.get(subscriptionId) || {};
      if (typeof subscriptionFailedCallback === "function") {
        subscriptionFailedCallback();
      }
    }
  }
  // Waiting that subscription has been connected before trying to unsubscribe
  async _waitForSubscriptionToBeConnected(subscriptionId) {
    const subscriptionObserver = this.subscriptionObserverMap.get(subscriptionId);
    if (subscriptionObserver) {
      const { subscriptionState } = subscriptionObserver;
      if (subscriptionState === SUBSCRIPTION_STATUS.PENDING) {
        return new Promise((resolve4, reject) => {
          const { observer, subscriptionState: observedSubscriptionState, variables, query } = subscriptionObserver;
          this.subscriptionObserverMap.set(subscriptionId, {
            observer,
            subscriptionState: observedSubscriptionState,
            variables,
            query,
            subscriptionReadyCallback: resolve4,
            subscriptionFailedCallback: reject
          });
        });
      }
    }
  }
  _sendUnsubscriptionMessage(subscriptionId) {
    try {
      if (this.awsRealTimeSocket && this.awsRealTimeSocket.readyState === WebSocket.OPEN && this.socketStatus === SOCKET_STATUS.READY) {
        const unsubscribeMessage = this._unsubscribeMessage(subscriptionId);
        const stringToAWSRealTime = JSON.stringify(unsubscribeMessage);
        this.awsRealTimeSocket.send(stringToAWSRealTime);
      }
    } catch (err) {
      this.logger.debug({ err });
    }
  }
  _removeSubscriptionObserver(subscriptionId) {
    this.subscriptionObserverMap.delete(subscriptionId);
    if (!this.allowNoSubscriptions) {
      setTimeout(this._closeSocketIfRequired.bind(this), 1e3);
    }
  }
  _closeSocketIfRequired() {
    if (this.subscriptionObserverMap.size > 0) {
      return;
    }
    if (!this.awsRealTimeSocket) {
      this.socketStatus = SOCKET_STATUS.CLOSED;
      return;
    }
    this.connectionStateMonitor.record(CONNECTION_CHANGE.CLOSING_CONNECTION);
    if (this.awsRealTimeSocket.bufferedAmount > 0) {
      setTimeout(this._closeSocketIfRequired.bind(this), 1e3);
    } else {
      this.logger.debug("closing WebSocket...");
      const tempSocket = this.awsRealTimeSocket;
      tempSocket.onclose = null;
      tempSocket.onerror = null;
      tempSocket.close(1e3);
      this.awsRealTimeSocket = void 0;
      this.socketStatus = SOCKET_STATUS.CLOSED;
      this._closeSocket();
    }
  }
  maintainKeepAlive() {
    this.keepAliveTimestamp = Date.now();
  }
  keepAliveHeartbeat(connectionTimeoutMs) {
    const currentTime = Date.now();
    if (currentTime - this.keepAliveTimestamp > DEFAULT_KEEP_ALIVE_ALERT_TIMEOUT) {
      this.connectionStateMonitor.record(CONNECTION_CHANGE.KEEP_ALIVE_MISSED);
    } else {
      this.connectionStateMonitor.record(CONNECTION_CHANGE.KEEP_ALIVE);
    }
    if (currentTime - this.keepAliveTimestamp > connectionTimeoutMs) {
      this._errorDisconnect(CONTROL_MSG.TIMEOUT_DISCONNECT);
    }
  }
  _handleIncomingSubscriptionMessage(message) {
    if (typeof message.data !== "string") {
      return;
    }
    const [isData, data] = this._handleSubscriptionData(message);
    if (isData) {
      this.maintainKeepAlive();
      return;
    }
    const { type, id, payload } = data;
    const { observer = null, query = "", variables = {}, startAckTimeoutId, subscriptionReadyCallback, subscriptionFailedCallback } = this.subscriptionObserverMap.get(id) || {};
    if (type === MESSAGE_TYPES.GQL_START_ACK || type === MESSAGE_TYPES.EVENT_SUBSCRIBE_ACK) {
      this.logger.debug(`subscription ready for ${JSON.stringify({ query, variables })}`);
      if (typeof subscriptionReadyCallback === "function") {
        subscriptionReadyCallback();
      }
      if (startAckTimeoutId)
        clearTimeout(startAckTimeoutId);
      dispatchApiEvent({
        event: CONTROL_MSG.SUBSCRIPTION_ACK,
        data: { query, variables },
        message: "Connection established for subscription"
      });
      const subscriptionState = SUBSCRIPTION_STATUS.CONNECTED;
      if (observer) {
        this.subscriptionObserverMap.set(id, {
          observer,
          query,
          variables,
          startAckTimeoutId: void 0,
          subscriptionState,
          subscriptionReadyCallback,
          subscriptionFailedCallback
        });
      }
      this.connectionStateMonitor.record(CONNECTION_CHANGE.CONNECTION_ESTABLISHED);
      return;
    }
    if (type === MESSAGE_TYPES.GQL_CONNECTION_KEEP_ALIVE) {
      this.maintainKeepAlive();
      return;
    }
    if (type === MESSAGE_TYPES.GQL_ERROR || type === MESSAGE_TYPES.EVENT_SUBSCRIBE_ERROR) {
      const subscriptionState = SUBSCRIPTION_STATUS.FAILED;
      if (observer) {
        this.subscriptionObserverMap.set(id, {
          observer,
          query,
          variables,
          startAckTimeoutId,
          subscriptionReadyCallback,
          subscriptionFailedCallback,
          subscriptionState
        });
        let errorMessage = JSON.stringify(payload ?? data);
        if (type === MESSAGE_TYPES.EVENT_SUBSCRIBE_ERROR) {
          const { errors } = JSON.parse(String(message.data));
          if (Array.isArray(errors) && errors.length > 0) {
            const error = errors[0];
            errorMessage = `${error.errorType}: ${error.message}`;
          }
        }
        this.logger.debug(`${CONTROL_MSG.CONNECTION_FAILED}: ${errorMessage}`);
        observer.error({
          errors: [
            {
              ...new GraphQLError(`${CONTROL_MSG.CONNECTION_FAILED}: ${errorMessage}`)
            }
          ]
        });
        if (startAckTimeoutId)
          clearTimeout(startAckTimeoutId);
        if (typeof subscriptionFailedCallback === "function") {
          subscriptionFailedCallback();
        }
      }
    }
  }
  _errorDisconnect(msg) {
    this.logger.debug(`Disconnect error: ${msg}`);
    if (this.awsRealTimeSocket) {
      this._closeSocket();
      this.awsRealTimeSocket.close();
    }
    this.socketStatus = SOCKET_STATUS.CLOSED;
  }
  _closeSocket() {
    if (this.keepAliveHeartbeatIntervalId) {
      clearInterval(this.keepAliveHeartbeatIntervalId);
      this.keepAliveHeartbeatIntervalId = void 0;
    }
    this.connectionStateMonitor.record(CONNECTION_CHANGE.CLOSED);
  }
  _timeoutStartSubscriptionAck(subscriptionId) {
    const subscriptionObserver = this.subscriptionObserverMap.get(subscriptionId);
    if (subscriptionObserver) {
      const { observer, query, variables } = subscriptionObserver;
      if (!observer) {
        return;
      }
      this.subscriptionObserverMap.set(subscriptionId, {
        observer,
        query,
        variables,
        subscriptionState: SUBSCRIPTION_STATUS.FAILED
      });
      this._closeSocket();
      this.logger.debug("timeoutStartSubscription", JSON.stringify({ query, variables }));
    }
  }
  _initializeWebSocketConnection({ appSyncGraphqlEndpoint, authenticationType, apiKey, region, additionalCustomHeaders }) {
    if (this.socketStatus === SOCKET_STATUS.READY) {
      return;
    }
    return new Promise(async (resolve4, reject) => {
      this.promiseArray.push({ res: resolve4, rej: reject });
      if (this.socketStatus === SOCKET_STATUS.CLOSED) {
        try {
          this.socketStatus = SOCKET_STATUS.CONNECTING;
          const payloadString = "{}";
          const authHeader = await awsRealTimeHeaderBasedAuth({
            authenticationType,
            payload: payloadString,
            canonicalUri: this.wsConnectUri,
            apiKey,
            appSyncGraphqlEndpoint,
            region,
            additionalCustomHeaders
          });
          const headerString = authHeader ? JSON.stringify(authHeader) : "";
          const encodedHeader = base64Encoder.convert(headerString, {
            urlSafe: true,
            skipPadding: true
          });
          const authTokenSubprotocol = `header-${encodedHeader}`;
          const queryParams = queryParamsFromCustomHeaders(additionalCustomHeaders);
          const awsRealTimeUrl = realtimeUrlWithQueryString(appSyncGraphqlEndpoint, queryParams);
          await this._establishRetryableConnection(awsRealTimeUrl, authTokenSubprotocol);
          this.promiseArray.forEach(({ res }) => {
            this.logger.debug("Notifying connection successful");
            res();
          });
          this.socketStatus = SOCKET_STATUS.READY;
          this.promiseArray = [];
        } catch (err) {
          this.logger.debug("Connection exited with", err);
          this.promiseArray.forEach(({ rej }) => {
            rej(err);
          });
          this.promiseArray = [];
          if (this.awsRealTimeSocket && this.awsRealTimeSocket.readyState === WebSocket.OPEN) {
            this.awsRealTimeSocket.close(3001);
          }
          this.awsRealTimeSocket = void 0;
          this.socketStatus = SOCKET_STATUS.CLOSED;
        }
      }
    });
  }
  async _establishRetryableConnection(awsRealTimeUrl, subprotocol) {
    this.logger.debug(`Establishing retryable connection`);
    await jitteredExponentialRetry(this._establishConnection.bind(this), [awsRealTimeUrl, subprotocol], MAX_DELAY_MS);
  }
  async _openConnection(awsRealTimeUrl, subprotocol) {
    return new Promise((resolve4, reject) => {
      const newSocket = this._getNewWebSocket(awsRealTimeUrl, [
        this.wsProtocolName,
        subprotocol
      ]);
      newSocket.onerror = () => {
        this.logger.debug(`WebSocket connection error`);
      };
      newSocket.onclose = () => {
        this._closeSocket();
        reject(new Error("Connection handshake error"));
      };
      newSocket.onopen = () => {
        this.awsRealTimeSocket = newSocket;
        resolve4();
      };
    });
  }
  _getNewWebSocket(url, protocol2) {
    return new WebSocket(url, protocol2);
  }
  async _initiateHandshake() {
    return new Promise((resolve4, reject) => {
      if (!this.awsRealTimeSocket) {
        reject(new Error("awsRealTimeSocket undefined"));
        return;
      }
      let ackOk = false;
      this.awsRealTimeSocket.onerror = (error) => {
        this.logger.debug(`WebSocket error ${JSON.stringify(error)}`);
      };
      this.awsRealTimeSocket.onclose = (event) => {
        this.logger.debug(`WebSocket closed ${event.reason}`);
        this._closeSocket();
        reject(new Error(JSON.stringify(event)));
      };
      this.awsRealTimeSocket.onmessage = (message) => {
        if (typeof message.data !== "string") {
          return;
        }
        this.logger.debug(`subscription message from AWS AppSyncRealTime: ${message.data} `);
        const data = JSON.parse(message.data);
        const { type } = data;
        const connectionTimeoutMs = this._extractConnectionTimeout(data);
        if (type === MESSAGE_TYPES.GQL_CONNECTION_ACK) {
          ackOk = true;
          this._registerWebsocketHandlers(connectionTimeoutMs);
          resolve4("Connected to AWS AppSyncRealTime");
          return;
        }
        if (type === MESSAGE_TYPES.GQL_CONNECTION_ERROR) {
          const { errorType, errorCode } = this._extractErrorCodeAndType(data);
          reject({ errorType, errorCode });
        }
      };
      const gqlInit = {
        type: MESSAGE_TYPES.GQL_CONNECTION_INIT
      };
      this.awsRealTimeSocket.send(JSON.stringify(gqlInit));
      const checkAckOk = (targetAckOk) => {
        if (!targetAckOk) {
          this.connectionStateMonitor.record(CONNECTION_CHANGE.CONNECTION_FAILED);
          reject(new Error(`Connection timeout: ack from AWSAppSyncRealTime was not received after ${CONNECTION_INIT_TIMEOUT} ms`));
        }
      };
      setTimeout(() => {
        checkAckOk(ackOk);
      }, CONNECTION_INIT_TIMEOUT);
    });
  }
  _registerWebsocketHandlers(connectionTimeoutMs) {
    if (!this.awsRealTimeSocket) {
      return;
    }
    this.keepAliveHeartbeatIntervalId = setInterval(() => {
      this.keepAliveHeartbeat(connectionTimeoutMs);
    }, DEFAULT_KEEP_ALIVE_HEARTBEAT_TIMEOUT);
    this.awsRealTimeSocket.onmessage = this._handleIncomingSubscriptionMessage.bind(this);
    this.awsRealTimeSocket.onerror = (err) => {
      this.logger.debug(err);
      this._errorDisconnect(CONTROL_MSG.CONNECTION_CLOSED);
    };
    this.awsRealTimeSocket.onclose = (event) => {
      this.logger.debug(`WebSocket closed ${event.reason}`);
      this._closeSocket();
      this._errorDisconnect(CONTROL_MSG.CONNECTION_CLOSED);
    };
  }
};

// node_modules/@aws-amplify/api-graphql/dist/esm/Providers/AWSAppSyncRealTimeProvider/index.mjs
var PROVIDER_NAME = "AWSAppSyncRealTimeProvider";
var WS_PROTOCOL_NAME = "graphql-ws";
var CONNECT_URI = "/connect";
var AWSAppSyncRealTimeProvider = class extends AWSWebSocketProvider {
  constructor() {
    super({
      providerName: PROVIDER_NAME,
      wsProtocolName: WS_PROTOCOL_NAME,
      connectUri: CONNECT_URI
    });
  }
  getProviderName() {
    return PROVIDER_NAME;
  }
  subscribe(options, customUserAgentDetails) {
    return super.subscribe(options, customUserAgentDetails);
  }
  async _prepareSubscriptionPayload({ options, subscriptionId, customUserAgentDetails, additionalCustomHeaders, libraryConfigHeaders }) {
    const { appSyncGraphqlEndpoint, authenticationType, query, variables, apiKey, region } = options;
    const data = {
      query,
      variables
    };
    const serializedData = JSON.stringify(data);
    const headers = {
      ...await awsRealTimeHeaderBasedAuth({
        apiKey,
        appSyncGraphqlEndpoint,
        authenticationType,
        payload: serializedData,
        canonicalUri: "",
        region,
        additionalCustomHeaders
      }),
      ...libraryConfigHeaders,
      ...additionalCustomHeaders,
      [USER_AGENT_HEADER]: getAmplifyUserAgent(customUserAgentDetails)
    };
    const subscriptionMessage = {
      id: subscriptionId,
      payload: {
        data: serializedData,
        extensions: {
          authorization: {
            ...headers
          }
        }
      },
      type: MESSAGE_TYPES.GQL_START
    };
    const serializedSubscriptionMessage = JSON.stringify(subscriptionMessage);
    return serializedSubscriptionMessage;
  }
  _handleSubscriptionData(message) {
    this.logger.debug(`subscription message from AWS AppSync RealTime: ${message.data}`);
    const { id = "", payload, type } = JSON.parse(String(message.data));
    const { observer = null, query = "", variables = {} } = this.subscriptionObserverMap.get(id) || {};
    this.logger.debug({ id, observer, query, variables });
    if (type === MESSAGE_TYPES.DATA && payload && payload.data) {
      if (observer) {
        observer.next(payload);
      } else {
        this.logger.debug(`observer not found for id: ${id}`);
      }
      return [true, { id, type, payload }];
    }
    return [false, { id, type, payload }];
  }
  _unsubscribeMessage(subscriptionId) {
    return {
      id: subscriptionId,
      type: MESSAGE_TYPES.GQL_STOP
    };
  }
  _extractConnectionTimeout(data) {
    const { payload: { connectionTimeoutMs = DEFAULT_KEEP_ALIVE_TIMEOUT } = {} } = data;
    return connectionTimeoutMs;
  }
  _extractErrorCodeAndType(data) {
    const { payload: { errors: [{ errorType = "", errorCode = 0 } = {}] = [] } = {} } = data;
    return { errorCode, errorType };
  }
};

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/errors/GraphQLApiError.mjs
var GraphQLApiError = class _GraphQLApiError extends AmplifyError {
  constructor(params) {
    super(params);
    this.constructor = _GraphQLApiError;
    Object.setPrototypeOf(this, _GraphQLApiError.prototype);
  }
};

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/errors/validation.mjs
var APIValidationErrorCode;
(function(APIValidationErrorCode2) {
  APIValidationErrorCode2["NoAuthSession"] = "NoAuthSession";
  APIValidationErrorCode2["NoRegion"] = "NoRegion";
  APIValidationErrorCode2["NoCustomEndpoint"] = "NoCustomEndpoint";
})(APIValidationErrorCode || (APIValidationErrorCode = {}));
var validationErrorMap2 = {
  [APIValidationErrorCode.NoAuthSession]: {
    message: "Auth session should not be empty."
  },
  // TODO: re-enable when working in all test environments:
  // [APIValidationErrorCode.NoEndpoint]: {
  // 	message: 'Missing endpoint',
  // },
  [APIValidationErrorCode.NoRegion]: {
    message: "Missing region."
  },
  [APIValidationErrorCode.NoCustomEndpoint]: {
    message: "Custom endpoint region is present without custom endpoint."
  }
};

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/errors/assertValidationError.mjs
function assertValidationError2(assertion, name) {
  const { message, recoverySuggestion } = validationErrorMap2[name];
  if (!assertion) {
    throw new GraphQLApiError({ name, message, recoverySuggestion });
  }
}

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/resolveConfig.mjs
var logger3 = new ConsoleLogger("GraphQLAPI resolveConfig");
var resolveConfig = (amplify) => {
  var _a, _b;
  const config = amplify.getConfig();
  if (!((_a = config.API) == null ? void 0 : _a.GraphQL)) {
    logger3.warn("The API configuration is missing. This is likely due to Amplify.configure() not being called prior to generateClient().");
  }
  const { apiKey, customEndpoint, customEndpointRegion, defaultAuthMode, endpoint, region } = ((_b = config.API) == null ? void 0 : _b.GraphQL) ?? {};
  assertValidationError2(!(!customEndpoint && customEndpointRegion), APIValidationErrorCode.NoCustomEndpoint);
  return {
    apiKey,
    customEndpoint,
    customEndpointRegion,
    defaultAuthMode,
    endpoint,
    region
  };
};

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/resolveLibraryOptions.mjs
var resolveLibraryOptions2 = (amplify) => {
  var _a, _b, _c, _d, _e, _f;
  const headers = (_c = (_b = (_a = amplify.libraryOptions) == null ? void 0 : _a.API) == null ? void 0 : _b.GraphQL) == null ? void 0 : _c.headers;
  const withCredentials = (_f = (_e = (_d = amplify.libraryOptions) == null ? void 0 : _d.API) == null ? void 0 : _e.GraphQL) == null ? void 0 : _f.withCredentials;
  return { headers, withCredentials };
};

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/errors/repackageAuthError.mjs
function repackageUnauthorizedError(content) {
  if (content.errors && Array.isArray(content.errors)) {
    content.errors.forEach((e) => {
      if (isUnauthorizedError(e)) {
        e.message = "Unauthorized";
        e.recoverySuggestion = `If you're calling an Amplify-generated API, make sure to set the "authMode" in generateClient({ authMode: '...' }) to the backend authorization rule's auth provider ('apiKey', 'userPool', 'iam', 'oidc', 'lambda')`;
      }
    });
  }
  return content;
}
function isUnauthorizedError(error) {
  var _a, _b, _c, _d;
  if ((_b = (_a = error == null ? void 0 : error.originalError) == null ? void 0 : _a.name) == null ? void 0 : _b.startsWith("UnauthorizedException")) {
    return true;
  }
  if (((_c = error.message) == null ? void 0 : _c.startsWith("Connection failed:")) && ((_d = error.message) == null ? void 0 : _d.includes("Permission denied"))) {
    return true;
  }
  return false;
}

// node_modules/@aws-amplify/api-graphql/dist/esm/types/index.mjs
var GraphQLAuthError;
(function(GraphQLAuthError2) {
  GraphQLAuthError2["NO_API_KEY"] = "No api-key configured";
  GraphQLAuthError2["NO_CURRENT_USER"] = "No current user";
  GraphQLAuthError2["NO_CREDENTIALS"] = "No credentials";
  GraphQLAuthError2["NO_FEDERATED_JWT"] = "No federated jwt";
  GraphQLAuthError2["NO_AUTH_TOKEN"] = "No auth token specified";
})(GraphQLAuthError || (GraphQLAuthError = {}));
var __amplify = Symbol("amplify");
var __authMode = Symbol("authMode");
var __authToken = Symbol("authToken");
var __apiKey = Symbol("apiKey");
var __headers = Symbol("headers");
var __endpoint = Symbol("endpoint");
function getInternals(client) {
  const c = client;
  return {
    amplify: c[__amplify],
    apiKey: c[__apiKey],
    authMode: c[__authMode],
    authToken: c[__authToken],
    endpoint: c[__endpoint],
    headers: c[__headers]
  };
}

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/errors/constants.mjs
var NO_API_KEY = {
  name: "NoApiKey",
  // ideal: No API key configured.
  message: GraphQLAuthError.NO_API_KEY,
  recoverySuggestion: 'The API request was made with `authMode: "apiKey"` but no API Key was passed into `Amplify.configure()`. Review if your API key is passed into the `Amplify.configure()` function.'
};
var NO_VALID_CREDENTIALS = {
  name: "NoCredentials",
  // ideal: No auth credentials available.
  message: GraphQLAuthError.NO_CREDENTIALS,
  recoverySuggestion: `The API request was made with \`authMode: "iam"\` but no authentication credentials are available.

If you intended to make a request using an authenticated role, review if your user is signed in before making the request.

If you intend to make a request using an unauthenticated role or also known as "guest access", verify if "Auth.Cognito.allowGuestAccess" is set to "true" in the \`Amplify.configure()\` function.`
};
var NO_VALID_AUTH_TOKEN = {
  name: "NoValidAuthTokens",
  // ideal: No valid JWT auth token provided to make the API request..
  message: GraphQLAuthError.NO_FEDERATED_JWT,
  recoverySuggestion: "If you intended to make an authenticated API request, review if the current user is signed in."
};
var NO_SIGNED_IN_USER = {
  name: "NoSignedUser",
  // ideal: Couldn't retrieve authentication credentials to make the API request.
  message: GraphQLAuthError.NO_CURRENT_USER,
  recoverySuggestion: "Review the underlying exception field for more details. If you intended to make an authenticated API request, review if the current user is signed in."
};
var NO_AUTH_TOKEN_HEADER = {
  name: "NoAuthorizationHeader",
  // ideal: Authorization header not specified.
  message: GraphQLAuthError.NO_AUTH_TOKEN,
  recoverySuggestion: 'The API request was made with `authMode: "lambda"` but no `authToken` is set. Review if a valid authToken is passed into the request options or in the `Amplify.configure()` function.'
};
var NO_ENDPOINT = {
  name: "NoEndpoint",
  message: "No GraphQL endpoint configured in `Amplify.configure()`.",
  recoverySuggestion: "Review if the GraphQL API endpoint is set in the `Amplify.configure()` function."
};

// node_modules/@aws-amplify/api-graphql/dist/esm/utils/errors/createGraphQLResultWithError.mjs
var createGraphQLResultWithError = (error) => {
  return {
    data: {},
    errors: [new GraphQLError(error.message, null, null, null, null, error)]
  };
};

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/utils/runtimeTypeGuards/isGraphQLResponseWithErrors.mjs
function isGraphQLResponseWithErrors(response) {
  if (!response) {
    return false;
  }
  const r = response;
  return Array.isArray(r.errors) && r.errors.length > 0;
}

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/graphqlAuth.mjs
async function headerBasedAuth(amplify, authMode, apiKey, additionalHeaders = {}) {
  var _a;
  let headers = {};
  switch (authMode) {
    case "apiKey":
      if (!apiKey) {
        throw new GraphQLApiError(NO_API_KEY);
      }
      headers = {
        "X-Api-Key": apiKey
      };
      break;
    case "iam": {
      const session = await amplify.Auth.fetchAuthSession();
      if (session.credentials === void 0) {
        throw new GraphQLApiError(NO_VALID_CREDENTIALS);
      }
      break;
    }
    case "oidc":
    case "userPool": {
      let token;
      try {
        token = (_a = (await amplify.Auth.fetchAuthSession()).tokens) == null ? void 0 : _a.accessToken.toString();
      } catch (e) {
        throw new GraphQLApiError({
          ...NO_SIGNED_IN_USER,
          underlyingError: e
        });
      }
      if (!token) {
        throw new GraphQLApiError(NO_VALID_AUTH_TOKEN);
      }
      headers = {
        Authorization: token
      };
      break;
    }
    case "lambda":
      if (typeof additionalHeaders === "object" && !additionalHeaders.Authorization) {
        throw new GraphQLApiError(NO_AUTH_TOKEN_HEADER);
      }
      headers = {
        Authorization: additionalHeaders.Authorization
      };
      break;
  }
  return headers;
}

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/InternalGraphQLAPI.mjs
var USER_AGENT_HEADER2 = "x-amz-user-agent";
var isAmplifyInstance = (amplify) => {
  return typeof amplify !== "function";
};
var InternalGraphQLAPIClass = class {
  constructor() {
    this.appSyncRealTime = /* @__PURE__ */ new Map();
    this._api = {
      post: post3,
      cancelREST: cancel,
      isCancelErrorREST: isCancelError,
      updateRequestToBeCancellable
    };
  }
  getModuleName() {
    return "InternalGraphQLAPI";
  }
  /**
   * to get the operation type
   * @param operation
   */
  getGraphqlOperationType(operation) {
    const doc = parse(operation);
    const definitions = doc.definitions;
    const [{ operation: operationType }] = definitions;
    return operationType;
  }
  /**
   * Executes a GraphQL operation
   *
   * @param options - GraphQL Options
   * @param [additionalHeaders] - headers to merge in after any `libraryConfigHeaders` set in the config
   * @returns An Observable if the query is a subscription query, else a promise of the graphql result.
   */
  graphql(amplify, { query: paramQuery, variables = {}, authMode, authToken, endpoint, apiKey }, additionalHeaders, customUserAgentDetails) {
    const query = typeof paramQuery === "string" ? parse(paramQuery) : parse(print(paramQuery));
    const [operationDef = {}] = query.definitions.filter((def) => def.kind === "OperationDefinition");
    const { operation: operationType } = operationDef;
    const headers = additionalHeaders || {};
    switch (operationType) {
      case "query":
      case "mutation": {
        const abortController = new AbortController();
        let responsePromise;
        if (isAmplifyInstance(amplify)) {
          responsePromise = this._graphql(amplify, { query, variables, authMode, apiKey, endpoint }, headers, abortController, customUserAgentDetails, authToken);
        } else {
          const wrapper = async (amplifyInstance) => {
            const result = await this._graphql(amplifyInstance, { query, variables, authMode, apiKey, endpoint }, headers, abortController, customUserAgentDetails, authToken);
            return result;
          };
          responsePromise = amplify(wrapper);
        }
        this._api.updateRequestToBeCancellable(responsePromise, abortController);
        return responsePromise;
      }
      case "subscription":
        return this._graphqlSubscribe(amplify, { query, variables, authMode, apiKey, endpoint }, headers, customUserAgentDetails, authToken);
      default:
        throw new Error(`invalid operation type: ${operationType}`);
    }
  }
  async _graphql(amplify, { query, variables, authMode: authModeOverride, endpoint: endpointOverride, apiKey: apiKeyOverride }, additionalHeaders = {}, abortController, customUserAgentDetails, authToken) {
    const { apiKey, region, endpoint: appSyncGraphqlEndpoint, customEndpoint, customEndpointRegion, defaultAuthMode } = resolveConfig(amplify);
    const initialAuthMode = authModeOverride || defaultAuthMode || "iam";
    const authMode = initialAuthMode === "identityPool" ? "iam" : initialAuthMode;
    const { headers: customHeaders, withCredentials } = resolveLibraryOptions2(amplify);
    let additionalCustomHeaders;
    if (typeof additionalHeaders === "function") {
      const requestOptions = {
        method: "POST",
        url: new AmplifyUrl(endpointOverride || customEndpoint || appSyncGraphqlEndpoint || "").toString(),
        queryString: print(query)
      };
      additionalCustomHeaders = await additionalHeaders(requestOptions);
    } else {
      additionalCustomHeaders = additionalHeaders;
    }
    if (authToken) {
      additionalCustomHeaders = {
        ...additionalCustomHeaders,
        Authorization: authToken
      };
    }
    const authHeaders = await headerBasedAuth(amplify, authMode, apiKeyOverride ?? apiKey, additionalCustomHeaders);
    const headers = {
      ...!customEndpoint && authHeaders,
      /**
       * Custom endpoint headers.
       * If there is both a custom endpoint and custom region present, we get the headers.
       * If there is a custom endpoint but no region, we return an empty object.
       * If neither are present, we return an empty object.
       */
      ...customEndpoint && (customEndpointRegion ? authHeaders : {}) || {},
      // Custom headers included in Amplify configuration options:
      ...customHeaders && await customHeaders({
        query: print(query),
        variables
      }),
      // Custom headers from individual requests or API client configuration:
      ...additionalCustomHeaders,
      // User agent headers:
      ...!customEndpoint && {
        [USER_AGENT_HEADER2]: getAmplifyUserAgent(customUserAgentDetails)
      }
    };
    const body = {
      query: print(query),
      variables: variables || null
    };
    let signingServiceInfo;
    if (customEndpoint && !customEndpointRegion || authMode !== "oidc" && authMode !== "userPool" && authMode !== "iam" && authMode !== "lambda") {
      signingServiceInfo = void 0;
    } else {
      signingServiceInfo = {
        service: !customEndpointRegion ? "appsync" : "execute-api",
        region: !customEndpointRegion ? region : customEndpointRegion
      };
    }
    const endpoint = endpointOverride || customEndpoint || appSyncGraphqlEndpoint;
    if (!endpoint) {
      throw createGraphQLResultWithError(new GraphQLApiError(NO_ENDPOINT));
    }
    let response;
    try {
      const { body: responseBody } = await this._api.post(amplify, {
        url: new AmplifyUrl(endpoint),
        options: {
          headers,
          body,
          signingServiceInfo,
          withCredentials
        },
        abortController
      });
      response = await responseBody.json();
    } catch (error) {
      if (this.isCancelError(error)) {
        throw error;
      }
      response = createGraphQLResultWithError(error);
    }
    if (isGraphQLResponseWithErrors(response)) {
      throw repackageUnauthorizedError(response);
    }
    return response;
  }
  /**
   * Checks to see if an error thrown is from an api request cancellation
   * @param {any} error - Any error
   * @return {boolean} - A boolean indicating if the error was from an api request cancellation
   */
  isCancelError(error) {
    return this._api.isCancelErrorREST(error);
  }
  /**
   * Cancels an inflight request. Only applicable for graphql queries and mutations
   * @param {any} request - request to cancel
   * @returns - A boolean indicating if the request was cancelled
   */
  cancel(request, message) {
    return this._api.cancelREST(request, message);
  }
  _graphqlSubscribe(amplify, { query, variables, authMode: authModeOverride, apiKey: apiKeyOverride, endpoint }, additionalHeaders = {}, customUserAgentDetails, authToken) {
    const config = resolveConfig(amplify);
    const initialAuthMode = authModeOverride || (config == null ? void 0 : config.defaultAuthMode) || "iam";
    const authMode = initialAuthMode === "identityPool" ? "iam" : initialAuthMode;
    const { headers: libraryConfigHeaders } = resolveLibraryOptions2(amplify);
    const appSyncGraphqlEndpoint = endpoint ?? (config == null ? void 0 : config.endpoint);
    const memoKey = appSyncGraphqlEndpoint ?? "none";
    const realtimeProvider = this.appSyncRealTime.get(memoKey) ?? new AWSAppSyncRealTimeProvider();
    this.appSyncRealTime.set(memoKey, realtimeProvider);
    return realtimeProvider.subscribe({
      query: print(query),
      variables,
      appSyncGraphqlEndpoint,
      region: config == null ? void 0 : config.region,
      authenticationType: authMode,
      apiKey: apiKeyOverride ?? (config == null ? void 0 : config.apiKey),
      additionalHeaders,
      authToken,
      libraryConfigHeaders
    }, customUserAgentDetails).pipe(catchError((e) => {
      if (e.errors) {
        throw repackageUnauthorizedError(e);
      }
      throw e;
    }));
  }
};
var InternalGraphQLAPI = new InternalGraphQLAPIClass();

// node_modules/@aws-amplify/data-schema-types/dist/esm/client/symbol.mjs
var __modelMeta__ = Symbol();

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/utils/resolveOwnerFields.mjs
function resolveOwnerFields(model) {
  const ownerFields = /* @__PURE__ */ new Set();
  for (const attr of model.attributes || []) {
    if (isAuthAttribute(attr)) {
      for (const rule of attr.properties.rules) {
        if (rule.allow === "owner") {
          ownerFields.add(rule.ownerField || "owner");
        } else if (rule.allow === "groups" && rule.groupsField !== void 0) {
          ownerFields.add(rule.groupsField);
        }
      }
    }
  }
  return Array.from(ownerFields);
}
function isAuthAttribute(attribute) {
  var _a, _b;
  if ((attribute == null ? void 0 : attribute.type) === "auth") {
    if (typeof (attribute == null ? void 0 : attribute.properties) === "object") {
      if (Array.isArray((_a = attribute == null ? void 0 : attribute.properties) == null ? void 0 : _a.rules)) {
        return ((_b = attribute == null ? void 0 : attribute.properties) == null ? void 0 : _b.rules).every((rule) => !!rule.allow);
      }
    }
  }
  return false;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/utils/stringTransformation.mjs
function capitalize(s) {
  return `${s[0].toUpperCase()}${s.slice(1)}`;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/utils/selfAwareAsync.mjs
function selfAwareAsync(resolver) {
  let resolve4;
  let reject;
  const resultPromise = new Promise((res, rej) => {
    resolve4 = res;
    reject = rej;
  });
  resolver(resultPromise).then((result) => {
    resolve4(result);
  }).catch((error) => {
    reject(error);
  });
  return resultPromise;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/cancellation.mjs
var promiseMap = /* @__PURE__ */ new WeakMap();
function extendCancellability(existingCancellablePromise, newPromiseToRegister) {
  promiseMap.set(newPromiseToRegister, existingCancellablePromise);
  return existingCancellablePromise.finally(() => {
    promiseMap.delete(newPromiseToRegister);
  });
}
function upgradeClientCancellation(client) {
  const innerCancel = client.cancel.bind(client);
  client.cancel = function(promise, message) {
    const visited = /* @__PURE__ */ new Set();
    let targetPromise = promise;
    while (targetPromise && promiseMap.has(targetPromise)) {
      if (visited.has(targetPromise))
        throw new Error("A cycle was detected in the modeled graphql cancellation chain. This is a bug. Please report it!");
      visited.add(targetPromise);
      targetPromise = promiseMap.get(targetPromise);
    }
    return innerCancel(targetPromise, message);
  };
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/APIClient.mjs
var connectionType = {
  HAS_ONE: "HAS_ONE",
  HAS_MANY: "HAS_MANY",
  BELONGS_TO: "BELONGS_TO"
};
var skGraphQlFieldTypeMap = {
  ID: "ID",
  String: "String",
  AWSDate: "String",
  AWSTime: "String",
  AWSDateTime: "String",
  AWSTimestamp: "Int",
  AWSEmail: "String",
  AWSPhone: "String",
  AWSURL: "String",
  AWSIPAddress: "String",
  AWSJSON: "String",
  Boolean: "Boolean",
  Int: "Int",
  Float: "Float"
};
var resolvedSkName = (sk) => {
  if (sk.length === 1) {
    return sk[0];
  } else {
    return sk.reduce((acc, curr, idx) => {
      if (idx === 0) {
        return curr;
      } else {
        return acc + capitalize(curr);
      }
    }, "");
  }
};
var flattenItems = (modelIntrospection, modelName, modelRecord) => {
  var _a;
  if (!modelRecord)
    return null;
  const mapped = {};
  for (const [fieldName, value] of Object.entries(modelRecord)) {
    const fieldDef = modelName ? (_a = modelIntrospection.models[modelName]) == null ? void 0 : _a.fields[fieldName] : void 0;
    const dvPair = { fieldDef, value };
    if (isRelatedModelItemsArrayPair(dvPair)) {
      mapped[fieldName] = dvPair.value.items.map((itemValue) => flattenItems(modelIntrospection, dvPair.fieldDef.type.model, itemValue));
    } else if (isRelatedModelProperty(fieldDef)) {
      mapped[fieldName] = flattenItems(modelIntrospection, fieldDef.type.model, value);
    } else {
      mapped[fieldName] = value;
    }
  }
  return mapped;
};
function isRelatedModelItemsArrayPair(dv) {
  var _a, _b;
  return typeof ((_a = dv.fieldDef) == null ? void 0 : _a.type) === "object" && "model" in dv.fieldDef.type && typeof dv.fieldDef.type.model === "string" && dv.fieldDef.isArray && Array.isArray((_b = dv.value) == null ? void 0 : _b.items);
}
function isRelatedModelProperty(fieldDef) {
  return typeof (fieldDef == null ? void 0 : fieldDef.type) === "object" && "model" in fieldDef.type && typeof fieldDef.type.model === "string";
}
function initializeModel(client, modelName, result, modelIntrospection, authMode, authToken, context = false) {
  const introModel = modelIntrospection.models[modelName];
  const introModelFields = introModel.fields;
  const modelFields = Object.entries(introModelFields).filter(([_, field]) => {
    var _a;
    return ((_a = field == null ? void 0 : field.type) == null ? void 0 : _a.model) !== void 0;
  }).map(([fieldName]) => fieldName);
  return result.map((record) => {
    var _a, _b, _c, _d, _e;
    if (record === null || record === void 0) {
      return record;
    }
    const initializedRelationshipFields = {};
    for (const fieldName of modelFields) {
      const modelField = introModelFields[fieldName];
      const modelFieldType = modelField == null ? void 0 : modelField.type;
      const relatedModelName = modelFieldType.model;
      const relatedModel = modelIntrospection.models[relatedModelName];
      const relatedModelPKFieldName = relatedModel.primaryKeyInfo.primaryKeyFieldName;
      const relatedModelSKFieldNames = relatedModel.primaryKeyInfo.sortKeyFieldNames;
      const relationType = (_a = modelField.association) == null ? void 0 : _a.connectionType;
      let connectionFields = [];
      if (modelField.association && "associatedWith" in modelField.association) {
        connectionFields = modelField.association.associatedWith;
      }
      const targetNames = [];
      if (modelField.association && "targetNames" in modelField.association) {
        targetNames.push(...modelField.association.targetNames);
      }
      switch (relationType) {
        case connectionType.BELONGS_TO: {
          const sortKeyValues = relatedModelSKFieldNames.reduce(
            // TODO(Eslint): is this implementation correct?
            // eslint-disable-next-line array-callback-return
            (acc, curVal) => {
              if (record[curVal]) {
                acc[curVal] = record[curVal];
              }
              return acc;
            },
            {}
          );
          if (((_b = client.models[relatedModelName]) == null ? void 0 : _b.get) === void 0) {
            break;
          }
          if (context) {
            initializedRelationshipFields[fieldName] = (contextSpec, options) => {
              if (record[targetNames[0]]) {
                return client.models[relatedModelName].get(contextSpec, {
                  [relatedModelPKFieldName]: record[targetNames[0]],
                  ...sortKeyValues
                }, {
                  authMode: (options == null ? void 0 : options.authMode) || authMode,
                  authToken: (options == null ? void 0 : options.authToken) || authToken
                });
              }
              return { data: null };
            };
          } else {
            initializedRelationshipFields[fieldName] = (options) => {
              if (record[targetNames[0]]) {
                return client.models[relatedModelName].get({
                  [relatedModelPKFieldName]: record[targetNames[0]],
                  ...sortKeyValues
                }, {
                  authMode: (options == null ? void 0 : options.authMode) || authMode,
                  authToken: (options == null ? void 0 : options.authToken) || authToken
                });
              }
              return { data: null };
            };
          }
          break;
        }
        case connectionType.HAS_ONE:
        case connectionType.HAS_MANY: {
          const mapResult = relationType === connectionType.HAS_ONE ? (result2) => {
            return {
              data: (result2 == null ? void 0 : result2.data.shift()) || null,
              errors: result2.errors,
              extensions: result2.extensions
            };
          } : (result2) => result2;
          const parentPk = introModel.primaryKeyInfo.primaryKeyFieldName;
          const parentSK = introModel.primaryKeyInfo.sortKeyFieldNames;
          const relatedModelField = relatedModel.fields[connectionFields[0]];
          const relatedModelFieldType = relatedModelField.type;
          if (relatedModelFieldType.model) {
            let relatedTargetNames = [];
            if (relatedModelField.association && "targetNames" in relatedModelField.association) {
              relatedTargetNames = (_c = relatedModelField.association) == null ? void 0 : _c.targetNames;
            }
            const hasManyFilter2 = relatedTargetNames.map((field, idx) => {
              if (idx === 0) {
                return { [field]: { eq: record[parentPk] } };
              }
              return { [field]: { eq: record[parentSK[idx - 1]] } };
            });
            if (((_d = client.models[relatedModelName]) == null ? void 0 : _d.list) === void 0) {
              break;
            }
            if (context) {
              initializedRelationshipFields[fieldName] = (contextSpec, options) => {
                if (record[parentPk]) {
                  return selfAwareAsync(async (resultPromise) => {
                    const basePromise = client.models[relatedModelName].list(contextSpec, {
                      filter: { and: hasManyFilter2 },
                      limit: options == null ? void 0 : options.limit,
                      nextToken: options == null ? void 0 : options.nextToken,
                      authMode: (options == null ? void 0 : options.authMode) || authMode,
                      authToken: (options == null ? void 0 : options.authToken) || authToken
                    });
                    const extendedBase = extendCancellability(basePromise, resultPromise);
                    return mapResult(await extendedBase);
                  });
                }
                return [];
              };
            } else {
              initializedRelationshipFields[fieldName] = (options) => {
                if (record[parentPk]) {
                  return selfAwareAsync(async (resultPromise) => {
                    const basePromise = client.models[relatedModelName].list({
                      filter: { and: hasManyFilter2 },
                      limit: options == null ? void 0 : options.limit,
                      nextToken: options == null ? void 0 : options.nextToken,
                      authMode: (options == null ? void 0 : options.authMode) || authMode,
                      authToken: (options == null ? void 0 : options.authToken) || authToken
                    });
                    const extendedBase = extendCancellability(basePromise, resultPromise);
                    return mapResult(await extendedBase);
                  });
                }
                return [];
              };
            }
            break;
          }
          const hasManyFilter = connectionFields.map((field, idx) => {
            if (idx === 0) {
              return { [field]: { eq: record[parentPk] } };
            }
            return { [field]: { eq: record[parentSK[idx - 1]] } };
          });
          if (((_e = client.models[relatedModelName]) == null ? void 0 : _e.list) === void 0) {
            break;
          }
          if (context) {
            initializedRelationshipFields[fieldName] = (contextSpec, options) => {
              if (record[parentPk]) {
                return selfAwareAsync(async (resultPromise) => {
                  const basePromise = client.models[relatedModelName].list(contextSpec, {
                    filter: { and: hasManyFilter },
                    limit: options == null ? void 0 : options.limit,
                    nextToken: options == null ? void 0 : options.nextToken,
                    authMode: (options == null ? void 0 : options.authMode) || authMode,
                    authToken: (options == null ? void 0 : options.authToken) || authToken
                  });
                  const extendedBase = extendCancellability(basePromise, resultPromise);
                  return mapResult(await extendedBase);
                });
              }
              return [];
            };
          } else {
            initializedRelationshipFields[fieldName] = (options) => {
              if (record[parentPk]) {
                return selfAwareAsync(async (resultPromise) => {
                  const basePromise = client.models[relatedModelName].list({
                    filter: { and: hasManyFilter },
                    limit: options == null ? void 0 : options.limit,
                    nextToken: options == null ? void 0 : options.nextToken,
                    authMode: (options == null ? void 0 : options.authMode) || authMode,
                    authToken: (options == null ? void 0 : options.authToken) || authToken
                  });
                  const extendedBase = extendCancellability(basePromise, resultPromise);
                  return mapResult(await extendedBase);
                });
              }
              return [];
            };
          }
          break;
        }
      }
    }
    return { ...record, ...initializedRelationshipFields };
  });
}
var graphQLOperationsInfo = {
  CREATE: { operationPrefix: "create", usePlural: false },
  GET: { operationPrefix: "get", usePlural: false },
  UPDATE: { operationPrefix: "update", usePlural: false },
  DELETE: { operationPrefix: "delete", usePlural: false },
  LIST: { operationPrefix: "list", usePlural: true },
  INDEX_QUERY: { operationPrefix: "", usePlural: false },
  ONCREATE: { operationPrefix: "onCreate", usePlural: false },
  ONUPDATE: { operationPrefix: "onUpdate", usePlural: false },
  ONDELETE: { operationPrefix: "onDelete", usePlural: false },
  OBSERVEQUERY: { operationPrefix: "observeQuery", usePlural: false }
};
var SELECTION_SET_WILDCARD = "*";
var getDefaultSelectionSetForNonModelWithIR = (nonModelDefinition, modelIntrospection) => {
  const { fields: fields7 } = nonModelDefinition;
  const mappedFields = Object.values(fields7).map(({ type, name }) => {
    if (typeof type.enum === "string") {
      return [name, FIELD_IR];
    }
    if (typeof type.nonModel === "string") {
      return [
        name,
        getDefaultSelectionSetForNonModelWithIR(modelIntrospection.nonModels[type.nonModel], modelIntrospection)
      ];
    }
    if (typeof type === "string") {
      return [name, FIELD_IR];
    }
    return void 0;
  }).filter((pair) => pair !== void 0);
  return Object.fromEntries(mappedFields);
};
var getDefaultSelectionSetForModelWithIR = (modelDefinition, modelIntrospection) => {
  const { fields: fields7 } = modelDefinition;
  const mappedFields = Object.values(fields7).map(({ type, name }) => {
    if (typeof type.enum === "string" || typeof type === "string") {
      return [name, FIELD_IR];
    }
    if (typeof type.nonModel === "string") {
      return [
        name,
        getDefaultSelectionSetForNonModelWithIR(modelIntrospection.nonModels[type.nonModel], modelIntrospection)
      ];
    }
    return void 0;
  }).filter((pair) => pair !== void 0);
  const ownerFields = resolveOwnerFields(modelDefinition).map((field) => [
    field,
    FIELD_IR
  ]);
  return Object.fromEntries(mappedFields.concat(ownerFields));
};
function defaultSelectionSetForModel(modelDefinition) {
  const { fields: fields7 } = modelDefinition;
  const explicitFields = Object.values(fields7).map(({ type, name }) => {
    if (typeof type === "string")
      return name;
    if (typeof type === "object") {
      if (typeof (type == null ? void 0 : type.enum) === "string") {
        return name;
      } else if (typeof (type == null ? void 0 : type.nonModel) === "string") {
        return `${name}.${SELECTION_SET_WILDCARD}`;
      }
    }
    return void 0;
  }).filter(Boolean);
  const ownerFields = resolveOwnerFields(modelDefinition);
  return Array.from(new Set(explicitFields.concat(ownerFields)));
}
var FIELD_IR = "";
function customSelectionSetToIR(modelIntrospection, modelName, selectionSet) {
  const dotNotationToObject = (path, modelOrNonModelName) => {
    var _a, _b, _c, _d, _e, _f;
    const [fieldName, ...rest] = path.split(".");
    const nested = rest[0];
    const modelOrNonModelDefinition = modelIntrospection.models[modelOrNonModelName] ?? modelIntrospection.nonModels[modelOrNonModelName];
    const modelOrNonModelFields = modelOrNonModelDefinition == null ? void 0 : modelOrNonModelDefinition.fields;
    const relatedModel = (_b = (_a = modelOrNonModelFields == null ? void 0 : modelOrNonModelFields[fieldName]) == null ? void 0 : _a.type) == null ? void 0 : _b.model;
    const relatedModelDefinition = modelIntrospection.models[relatedModel];
    const relatedNonModel = (_d = (_c = modelOrNonModelFields == null ? void 0 : modelOrNonModelFields[fieldName]) == null ? void 0 : _c.type) == null ? void 0 : _d.nonModel;
    const relatedNonModelDefinition = modelIntrospection.nonModels[relatedNonModel];
    const isModelOrNonModelOrFieldType = relatedModelDefinition ? "model" : relatedNonModelDefinition ? "nonModel" : "field";
    if (isModelOrNonModelOrFieldType === "nonModel") {
      let result = {};
      if (!nested) {
        throw Error(`${fieldName} must declare a wildcard (*) or a field of custom type ${relatedNonModel}`);
      }
      if (nested === SELECTION_SET_WILDCARD) {
        result = {
          [fieldName]: getDefaultSelectionSetForNonModelWithIR(relatedNonModelDefinition, modelIntrospection)
        };
      } else {
        result = {
          [fieldName]: dotNotationToObject(rest.join("."), relatedNonModel)
        };
      }
      return result;
    } else if (isModelOrNonModelOrFieldType === "model") {
      let result = {};
      if (!nested) {
        throw Error(`${fieldName} must declare a wildcard (*) or a field of model ${relatedModel}`);
      }
      if (nested === SELECTION_SET_WILDCARD) {
        const nestedRelatedModelDefinition = modelIntrospection.models[relatedModel];
        result = {
          [fieldName]: getDefaultSelectionSetForModelWithIR(nestedRelatedModelDefinition, modelIntrospection)
        };
      } else {
        result = {
          [fieldName]: dotNotationToObject(rest.join("."), relatedModel)
        };
      }
      if ((_e = modelOrNonModelFields[fieldName]) == null ? void 0 : _e.isArray) {
        result = {
          [fieldName]: {
            items: result[fieldName]
          }
        };
      }
      return result;
    } else {
      const modelField = modelOrNonModelFields == null ? void 0 : modelOrNonModelFields[fieldName];
      const nonModelDefinition = modelIntrospection.nonModels[modelOrNonModelName];
      const nonModelField = (_f = nonModelDefinition == null ? void 0 : nonModelDefinition.fields) == null ? void 0 : _f[fieldName];
      if (!nonModelDefinition) {
        const isOwnerField = resolveOwnerFields(modelOrNonModelDefinition).includes(fieldName);
        if (!modelField && !isOwnerField) {
          throw Error(`${fieldName} is not a field of model ${modelOrNonModelName}`);
        }
      } else {
        if (!nonModelField) {
          throw Error(`${fieldName} is not a field of custom type ${modelOrNonModelName}`);
        }
      }
      return { [fieldName]: FIELD_IR };
    }
  };
  return selectionSet.reduce((resultObj, path) => deepMergeSelectionSetObjects(dotNotationToObject(path, modelName), resultObj), {});
}
function selectionSetIRToString(obj) {
  const res = [];
  Object.entries(obj).forEach(([fieldName, value]) => {
    if (value === FIELD_IR) {
      res.push(fieldName);
    } else if (typeof value === "object" && value !== null) {
      if (value == null ? void 0 : value.items) {
        res.push(fieldName, "{", "items", "{", selectionSetIRToString(value.items), "}", "}");
      } else {
        res.push(fieldName, "{", selectionSetIRToString(value), "}");
      }
    }
  });
  return res.join(" ");
}
function deepMergeSelectionSetObjects(source, target) {
  const isObject = (obj) => obj && typeof obj === "object";
  for (const key in source) {
    if (!Object.prototype.hasOwnProperty.call(source, key))
      continue;
    if (Object.prototype.hasOwnProperty.call(target, key) && isObject(target[key])) {
      deepMergeSelectionSetObjects(source[key], target[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}
function generateSelectionSet(modelIntrospection, modelName, selectionSet) {
  const modelDefinition = modelIntrospection.models[modelName];
  const selSetIr = customSelectionSetToIR(modelIntrospection, modelName, selectionSet ?? defaultSelectionSetForModel(modelDefinition));
  const selSetString = selectionSetIRToString(selSetIr);
  return selSetString;
}
function generateGraphQLDocument(modelIntrospection, modelDefinition, modelOperation, listArgs, indexMeta) {
  var _a, _b;
  const { name, pluralName, fields: fields7, primaryKeyInfo: { isCustomPrimaryKey, primaryKeyFieldName, sortKeyFieldNames }, attributes } = modelDefinition;
  const namePascalCase = name.charAt(0).toUpperCase() + name.slice(1);
  const pluralNamePascalCase = pluralName.charAt(0).toUpperCase() + pluralName.slice(1);
  const { operationPrefix, usePlural } = graphQLOperationsInfo[modelOperation];
  const { selectionSet } = listArgs || {};
  let graphQLFieldName;
  let indexQueryArgs;
  if (operationPrefix) {
    graphQLFieldName = `${operationPrefix}${usePlural ? pluralNamePascalCase : namePascalCase}`;
  } else if (indexMeta) {
    const { queryField, pk, sk = [] } = indexMeta;
    graphQLFieldName = queryField;
    let skQueryArgs = {};
    if (sk.length === 1) {
      const [skField] = sk;
      const type = typeof fields7[skField].type === "string" ? fields7[skField].type : "String";
      const normalizedType = skGraphQlFieldTypeMap[type];
      skQueryArgs = {
        [skField]: `Model${normalizedType}KeyConditionInput`
      };
    } else if (sk.length > 1) {
      const compositeSkArgName = resolvedSkName(sk);
      const keyName = (_b = (_a = attributes == null ? void 0 : attributes.find((attr) => {
        var _a2;
        return ((_a2 = attr == null ? void 0 : attr.properties) == null ? void 0 : _a2.queryField) === queryField;
      })) == null ? void 0 : _a.properties) == null ? void 0 : _b.name;
      skQueryArgs = {
        [compositeSkArgName]: `Model${capitalize(name)}${capitalize(keyName)}CompositeKeyConditionInput`
      };
    }
    indexQueryArgs = {
      [pk]: `${Object.prototype.hasOwnProperty.call(fields7[pk].type, "enum") ? fields7[pk].type.enum : fields7[pk].type}!`,
      ...skQueryArgs
    };
  } else {
    throw new Error("Error generating GraphQL Document - invalid operation name");
  }
  let graphQLOperationType;
  let graphQLSelectionSet;
  let graphQLArguments;
  const selectionSetFields = generateSelectionSet(modelIntrospection, name, selectionSet);
  const getPkArgs = {
    [primaryKeyFieldName]: `${fields7[primaryKeyFieldName].type}!`
  };
  const listPkArgs = {};
  const generateSkArgs = (op) => {
    if (sortKeyFieldNames.length === 0)
      return {};
    if (op === "get") {
      return sortKeyFieldNames.reduce((acc, fieldName) => {
        const fieldType = fields7[fieldName].type;
        if (op === "get") {
          acc[fieldName] = `${fieldType}!`;
        }
        return acc;
      }, {});
    } else {
      if (sortKeyFieldNames.length === 1) {
        const [sk] = sortKeyFieldNames;
        const type = typeof fields7[sk].type === "string" ? fields7[sk].type : "String";
        const normalizedType = skGraphQlFieldTypeMap[type];
        return {
          [sk]: `Model${normalizedType}KeyConditionInput`
        };
      } else {
        const compositeSkArgName = resolvedSkName(sortKeyFieldNames);
        return {
          [compositeSkArgName]: `Model${capitalize(name)}PrimaryCompositeKeyConditionInput`
        };
      }
    }
  };
  if (isCustomPrimaryKey) {
    Object.assign(getPkArgs, generateSkArgs("get"));
    Object.assign(listPkArgs, {
      // PK is only included in list query field args in the generated GQL
      // when explicitly specifying PK with .identifier(['fieldName']) or @primaryKey in the schema definition
      [primaryKeyFieldName]: `${fields7[primaryKeyFieldName].type}`,
      // PK is always a nullable arg for list (no `!` after the type)
      sortDirection: "ModelSortDirection"
    }, generateSkArgs("list"));
  }
  switch (modelOperation) {
    case "CREATE":
    case "UPDATE":
    case "DELETE":
      graphQLArguments ?? (graphQLArguments = {
        input: `${operationPrefix.charAt(0).toLocaleUpperCase() + operationPrefix.slice(1)}${namePascalCase}Input!`
      });
      graphQLOperationType ?? (graphQLOperationType = "mutation");
    case "GET":
      graphQLArguments ?? (graphQLArguments = getPkArgs);
      graphQLSelectionSet ?? (graphQLSelectionSet = selectionSetFields);
    case "LIST":
      graphQLArguments ?? (graphQLArguments = {
        ...listPkArgs,
        // eslint doesn't like the ts-ignore, because it thinks it's unnecessary.
        // But TS doesn't like the `filter: ...` because it think it will always be
        // overwritten. (it won't be.) so, we need to ignore the TS error and then
        // ignore the eslint error on the ts-ignore.
        // eslint-disable-next-line
        // @ts-ignore
        filter: `Model${namePascalCase}FilterInput`,
        limit: "Int",
        nextToken: "String"
      });
      graphQLOperationType ?? (graphQLOperationType = "query");
      graphQLSelectionSet ?? (graphQLSelectionSet = `items { ${selectionSetFields} } nextToken __typename`);
    case "INDEX_QUERY":
      graphQLArguments ?? (graphQLArguments = {
        ...indexQueryArgs,
        filter: `Model${namePascalCase}FilterInput`,
        sortDirection: "ModelSortDirection",
        limit: "Int",
        nextToken: "String"
      });
      graphQLOperationType ?? (graphQLOperationType = "query");
      graphQLSelectionSet ?? (graphQLSelectionSet = `items { ${selectionSetFields} } nextToken __typename`);
    case "ONCREATE":
    case "ONUPDATE":
    case "ONDELETE":
      graphQLArguments ?? (graphQLArguments = {
        filter: `ModelSubscription${namePascalCase}FilterInput`
      });
      graphQLOperationType ?? (graphQLOperationType = "subscription");
      graphQLSelectionSet ?? (graphQLSelectionSet = selectionSetFields);
      break;
    case "OBSERVEQUERY":
    default:
      throw new Error("Internal error: Attempted to generate graphql document for observeQuery. Please report this error.");
  }
  const graphQLDocument = `${graphQLOperationType}${graphQLArguments ? `(${Object.entries(graphQLArguments).map(([fieldName, type]) => `$${fieldName}: ${type}`)})` : ""} { ${graphQLFieldName}${graphQLArguments ? `(${Object.keys(graphQLArguments).map((fieldName) => `${fieldName}: $${fieldName}`)})` : ""} { ${graphQLSelectionSet} } }`;
  return graphQLDocument;
}
function buildGraphQLVariables(modelDefinition, operation, arg, modelIntrospection, indexMeta) {
  const { fields: fields7, primaryKeyInfo: { isCustomPrimaryKey, primaryKeyFieldName, sortKeyFieldNames } } = modelDefinition;
  const skName = (sortKeyFieldNames == null ? void 0 : sortKeyFieldNames.length) && resolvedSkName(sortKeyFieldNames);
  let variables = {};
  switch (operation) {
    case "CREATE":
      variables = {
        input: arg ? normalizeMutationInput(arg, modelDefinition, modelIntrospection) : {}
      };
      break;
    case "UPDATE":
      variables = {
        input: arg ? Object.fromEntries(Object.entries(normalizeMutationInput(arg, modelDefinition, modelIntrospection)).filter(([fieldName]) => {
          return fields7[fieldName] ? !fields7[fieldName].isReadOnly : !resolveOwnerFields(modelDefinition).includes(fieldName);
        })) : {}
      };
      break;
    case "GET":
    case "DELETE":
      if (arg) {
        variables = isCustomPrimaryKey ? [primaryKeyFieldName, ...sortKeyFieldNames].reduce((acc, fieldName) => {
          acc[fieldName] = arg[fieldName];
          return acc;
        }, {}) : { [primaryKeyFieldName]: arg[primaryKeyFieldName] };
      }
      if (operation === "DELETE") {
        variables = { input: variables };
      }
      break;
    case "LIST":
      if (arg == null ? void 0 : arg.filter) {
        variables.filter = arg.filter;
      }
      if (arg == null ? void 0 : arg.sortDirection) {
        variables.sortDirection = arg.sortDirection;
      }
      if (arg && arg[primaryKeyFieldName]) {
        variables[primaryKeyFieldName] = arg[primaryKeyFieldName];
      }
      if (skName && arg && arg[skName]) {
        variables[skName] = arg[skName];
      }
      if (arg == null ? void 0 : arg.nextToken) {
        variables.nextToken = arg.nextToken;
      }
      if (arg == null ? void 0 : arg.limit) {
        variables.limit = arg.limit;
      }
      break;
    case "INDEX_QUERY": {
      const { pk, sk = [] } = indexMeta;
      const indexQuerySkName = (sk == null ? void 0 : sk.length) && resolvedSkName(sk);
      variables[pk] = arg[pk];
      if (indexQuerySkName && arg && arg[indexQuerySkName]) {
        variables[indexQuerySkName] = arg[indexQuerySkName];
      }
      if (arg == null ? void 0 : arg.filter) {
        variables.filter = arg.filter;
      }
      if (arg == null ? void 0 : arg.sortDirection) {
        variables.sortDirection = arg.sortDirection;
      }
      if (arg == null ? void 0 : arg.nextToken) {
        variables.nextToken = arg.nextToken;
      }
      if (arg == null ? void 0 : arg.limit) {
        variables.limit = arg.limit;
      }
      break;
    }
    case "ONCREATE":
    case "ONUPDATE":
    case "ONDELETE":
      if (arg == null ? void 0 : arg.filter) {
        variables = { filter: arg.filter };
      }
      break;
    case "OBSERVEQUERY":
      throw new Error("Internal error: Attempted to build variables for observeQuery. Please report this error.");
    default: {
      const exhaustiveCheck = operation;
      throw new Error(`Unhandled operation case: ${exhaustiveCheck}`);
    }
  }
  return variables;
}
function normalizeMutationInput(mutationInput, model, modelIntrospection) {
  const { fields: fields7 } = model;
  const normalized = {};
  Object.entries(mutationInput).forEach(([inputFieldName, inputValue]) => {
    var _a, _b;
    const fieldType = (_a = fields7[inputFieldName]) == null ? void 0 : _a.type;
    const relatedModelName = fieldType == null ? void 0 : fieldType.model;
    if (relatedModelName) {
      const association = (_b = fields7[inputFieldName]) == null ? void 0 : _b.association;
      const relatedModelDef = modelIntrospection.models[relatedModelName];
      const relatedModelPkInfo = relatedModelDef.primaryKeyInfo;
      if ((association == null ? void 0 : association.connectionType) === connectionType.HAS_ONE) {
        const associationHasOne = association;
        associationHasOne.targetNames.forEach((targetName, idx) => {
          const associatedFieldName = associationHasOne.associatedWith[idx];
          normalized[targetName] = inputValue[associatedFieldName];
        });
      }
      if ((association == null ? void 0 : association.connectionType) === connectionType.BELONGS_TO) {
        const associationBelongsTo = association;
        associationBelongsTo.targetNames.forEach((targetName, idx) => {
          if (idx === 0) {
            const associatedFieldName = relatedModelPkInfo.primaryKeyFieldName;
            normalized[targetName] = inputValue[associatedFieldName];
          } else {
            const associatedFieldName = relatedModelPkInfo.sortKeyFieldNames[idx - 1];
            normalized[targetName] = inputValue[associatedFieldName];
          }
        });
      }
    } else {
      normalized[inputFieldName] = inputValue;
    }
  });
  return normalized;
}
function authModeParams(client, getInternals2, options = {}) {
  const internals = getInternals2(client);
  return {
    authMode: options.authMode || internals.authMode,
    authToken: options.authToken || internals.authToken
  };
}
function getCustomHeaders(client, getInternals2, requestHeaders2) {
  let headers = getInternals2(client).headers || {};
  if (requestHeaders2) {
    headers = requestHeaders2;
  }
  return headers;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/operations/utils.mjs
function handleListGraphQlError(error) {
  if (error == null ? void 0 : error.errors) {
    return {
      ...error,
      data: []
    };
  } else {
    throw error;
  }
}
function handleSingularGraphQlError(error) {
  if (error.errors) {
    return {
      ...error,
      data: null
    };
  } else {
    throw error;
  }
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/getCustomUserAgentDetails.mjs
var INTERNAL_USER_AGENT_OVERRIDE = Symbol("INTERNAL_USER_AGENT_OVERRIDE");
var AiAction;
(function(AiAction2) {
  AiAction2["CreateConversation"] = "1";
  AiAction2["GetConversation"] = "2";
  AiAction2["ListConversations"] = "3";
  AiAction2["DeleteConversation"] = "4";
  AiAction2["SendMessage"] = "5";
  AiAction2["ListMessages"] = "6";
  AiAction2["OnStreamEvent"] = "7";
  AiAction2["Generation"] = "8";
  AiAction2["UpdateConversation"] = "9";
})(AiAction || (AiAction = {}));
var getCustomUserAgentDetails = (action) => ({
  category: "ai",
  action
});
function createUserAgentOverride(customUserAgentDetails) {
  return customUserAgentDetails ? { [INTERNAL_USER_AGENT_OVERRIDE]: customUserAgentDetails } : void 0;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/operations/custom.mjs
var argIsContextSpec = (arg) => {
  var _a;
  return typeof ((_a = arg == null ? void 0 : arg.token) == null ? void 0 : _a.value) === "symbol";
};
function customOpFactory(client, modelIntrospection, operationType, operation, useContext, getInternals2, customUserAgentDetails) {
  const argsDefined = operation.arguments !== void 0;
  const op = (...args) => {
    const options = args[args.length - 1];
    let contextSpec;
    let arg;
    if (useContext) {
      if (argIsContextSpec(args[0])) {
        contextSpec = args[0];
      } else {
        throw new Error(`Invalid first argument passed to ${operation.name}. Expected contextSpec`);
      }
    }
    if (argsDefined) {
      if (useContext) {
        arg = args[1];
      } else {
        arg = args[0];
      }
    }
    if (operationType === "subscription") {
      return _opSubscription(
        // subscriptions are only enabled on the clientside
        client,
        modelIntrospection,
        operation,
        getInternals2,
        arg,
        options,
        customUserAgentDetails
      );
    }
    return _op(client, modelIntrospection, operationType, operation, getInternals2, arg, options, contextSpec, customUserAgentDetails);
  };
  return op;
}
function hasStringField(o, field) {
  return typeof o[field] === "string";
}
function isEnumType2(type) {
  return type instanceof Object && "enum" in type;
}
function isInputType2(type) {
  return type instanceof Object && "input" in type;
}
function argumentBaseTypeString({ type, isRequired }) {
  const requiredFlag = isRequired ? "!" : "";
  if (isEnumType2(type)) {
    return `${type.enum}${requiredFlag}`;
  }
  if (isInputType2(type)) {
    return `${type.input}${requiredFlag}`;
  }
  return `${type}${requiredFlag}`;
}
function outerArguments(operation) {
  if (operation.arguments === void 0) {
    return "";
  }
  const args = Object.entries(operation.arguments).map(([k, argument]) => {
    const baseType = argumentBaseTypeString(argument);
    const finalType = argument.isArray ? `[${baseType}]${argument.isArrayNullable ? "" : "!"}` : baseType;
    return `$${k}: ${finalType}`;
  }).join(", ");
  return args.length > 0 ? `(${args})` : "";
}
function innerArguments(operation) {
  if (operation.arguments === void 0) {
    return "";
  }
  const args = Object.keys(operation.arguments).map((k) => `${k}: $${k}`).join(", ");
  return args.length > 0 ? `(${args})` : "";
}
function operationSelectionSet(modelIntrospection, operation) {
  if (hasStringField(operation, "type") || hasStringField(operation.type, "enum")) {
    return "";
  } else if (hasStringField(operation.type, "nonModel")) {
    const nonModel = modelIntrospection.nonModels[operation.type.nonModel];
    return `{${selectionSetIRToString(getDefaultSelectionSetForNonModelWithIR(nonModel, modelIntrospection))}}`;
  } else if (hasStringField(operation.type, "model")) {
    return `{${generateSelectionSet(modelIntrospection, operation.type.model)}}`;
  } else {
    return "";
  }
}
function operationVariables(operation, args = {}) {
  const variables = {};
  if (operation.arguments === void 0) {
    return variables;
  }
  for (const argDef of Object.values(operation.arguments)) {
    if (typeof args[argDef.name] !== "undefined") {
      variables[argDef.name] = args[argDef.name];
    } else if (argDef.isRequired) {
      throw new Error(`${operation.name} requires arguments '${argDef.name}'`);
    }
  }
  return variables;
}
function _op(client, modelIntrospection, operationType, operation, getInternals2, args, options, context, customUserAgentDetails) {
  return selfAwareAsync(async (resultPromise) => {
    const { name: operationName } = operation;
    const auth = authModeParams(client, getInternals2, options);
    const headers = getCustomHeaders(client, getInternals2, options == null ? void 0 : options.headers);
    const outerArgsString = outerArguments(operation);
    const innerArgsString = innerArguments(operation);
    const selectionSet = operationSelectionSet(modelIntrospection, operation);
    const returnTypeModelName = hasStringField(operation.type, "model") ? operation.type.model : void 0;
    const query = `
    ${operationType.toLocaleLowerCase()}${outerArgsString} {
      ${operationName}${innerArgsString} ${selectionSet}
    }
  `;
    const variables = operationVariables(operation, args);
    const userAgentOverride = createUserAgentOverride(customUserAgentDetails);
    try {
      const basePromise = context ? client.graphql(context, {
        ...auth,
        query,
        variables
      }, headers) : client.graphql({
        ...auth,
        query,
        variables,
        ...userAgentOverride
      }, headers);
      const extendedPromise = extendCancellability(basePromise, resultPromise);
      const { data, extensions } = await extendedPromise;
      if (data) {
        const [key] = Object.keys(data);
        const isArrayResult = Array.isArray(data[key]);
        const flattenedResult = isArrayResult ? data[key].filter((x) => x) : data[key];
        const initialized = returnTypeModelName ? initializeModel(client, returnTypeModelName, isArrayResult ? flattenedResult : [flattenedResult], modelIntrospection, auth.authMode, auth.authToken, !!context) : flattenedResult;
        return {
          data: !isArrayResult && Array.isArray(initialized) ? initialized.shift() : initialized,
          extensions
        };
      } else {
        return { data: null, extensions };
      }
    } catch (error) {
      const { data, errors } = error;
      if (data && Object.keys(data).length !== 0 && errors) {
        const [key] = Object.keys(data);
        const isArrayResult = Array.isArray(data[key]);
        const flattenedResult = isArrayResult ? data[key].filter((x) => x) : data[key];
        if (flattenedResult) {
          const initialized = returnTypeModelName ? initializeModel(client, returnTypeModelName, isArrayResult ? flattenedResult : [flattenedResult], modelIntrospection, auth.authMode, auth.authToken, !!context) : flattenedResult;
          return {
            data: !isArrayResult && Array.isArray(initialized) ? initialized.shift() : initialized,
            errors
          };
        } else {
          return handleSingularGraphQlError(error);
        }
      } else {
        return handleSingularGraphQlError(error);
      }
    }
  });
}
function _opSubscription(client, modelIntrospection, operation, getInternals2, args, options, customUserAgentDetails) {
  const operationType = "subscription";
  const { name: operationName } = operation;
  const auth = authModeParams(client, getInternals2, options);
  const headers = getCustomHeaders(client, getInternals2, options == null ? void 0 : options.headers);
  const outerArgsString = outerArguments(operation);
  const innerArgsString = innerArguments(operation);
  const selectionSet = operationSelectionSet(modelIntrospection, operation);
  const returnTypeModelName = hasStringField(operation.type, "model") ? operation.type.model : void 0;
  const query = `
    ${operationType.toLocaleLowerCase()}${outerArgsString} {
      ${operationName}${innerArgsString} ${selectionSet}
    }
  `;
  const variables = operationVariables(operation, args);
  const userAgentOverride = createUserAgentOverride(customUserAgentDetails);
  const observable = client.graphql({
    ...auth,
    query,
    variables,
    ...userAgentOverride
  }, headers);
  return observable.pipe(map((value) => {
    const [key] = Object.keys(value.data);
    const data = value.data[key];
    const [initialized] = returnTypeModelName ? initializeModel(client, returnTypeModelName, [data], modelIntrospection, auth.authMode, auth.authToken) : [data];
    return initialized;
  }));
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/generateCustomOperationsProperty.mjs
var operationTypeMap = {
  queries: "query",
  mutations: "mutation",
  subscriptions: "subscription"
};
function generateCustomOperationsProperty(client, config, operationsType, getInternals2) {
  if (!config) {
    return {};
  }
  const modelIntrospection = config.modelIntrospection;
  if (!modelIntrospection) {
    return {};
  }
  const operations = modelIntrospection[operationsType];
  if (!operations) {
    return {};
  }
  const ops = {};
  const useContext = getInternals2(client).amplify === null;
  for (const operation of Object.values(operations)) {
    ops[operation.name] = customOpFactory(client, modelIntrospection, operationTypeMap[operationsType], operation, useContext, getInternals2);
  }
  return ops;
}
function generateCustomMutationsProperty(client, config, getInternals2) {
  return generateCustomOperationsProperty(client, config, "mutations", getInternals2);
}
function generateCustomQueriesProperty(client, config, getInternals2) {
  return generateCustomOperationsProperty(client, config, "queries", getInternals2);
}
function generateCustomSubscriptionsProperty(client, config, getInternals2) {
  return generateCustomOperationsProperty(client, config, "subscriptions", getInternals2);
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/operations/get.mjs
function getFactory(client, modelIntrospection, model, operation, getInternals2, useContext = false, customUserAgentDetails) {
  const getWithContext = (contextSpec, arg, options) => {
    return _get(client, modelIntrospection, model, arg, options, operation, getInternals2, contextSpec, customUserAgentDetails);
  };
  const get5 = (arg, options) => {
    return _get(client, modelIntrospection, model, arg, options, operation, getInternals2, void 0, customUserAgentDetails);
  };
  return useContext ? getWithContext : get5;
}
function _get(client, modelIntrospection, model, arg, options, operation, getInternals2, context, customUserAgentDetails) {
  return selfAwareAsync(async (resultPromise) => {
    const { name } = model;
    const query = generateGraphQLDocument(modelIntrospection, model, operation, options);
    const variables = buildGraphQLVariables(model, operation, arg, modelIntrospection);
    const auth = authModeParams(client, getInternals2, options);
    const headers = getCustomHeaders(client, getInternals2, options == null ? void 0 : options.headers);
    const userAgentOverride = createUserAgentOverride(customUserAgentDetails);
    try {
      const basePromise = context ? client.graphql(context, {
        ...auth,
        query,
        variables
      }, headers) : client.graphql({
        ...auth,
        query,
        variables,
        ...userAgentOverride
      }, headers);
      const extendedPromise = extendCancellability(basePromise, resultPromise);
      const { data, extensions } = await extendedPromise;
      if (data) {
        const [key] = Object.keys(data);
        const flattenedResult = flattenItems(modelIntrospection, name, data[key]);
        if (flattenedResult === null) {
          return { data: null, extensions };
        } else if (options == null ? void 0 : options.selectionSet) {
          return { data: flattenedResult, extensions };
        } else {
          const [initialized] = initializeModel(client, name, [flattenedResult], modelIntrospection, auth.authMode, auth.authToken, !!context);
          return { data: initialized, extensions };
        }
      } else {
        return { data: null, extensions };
      }
    } catch (error) {
      const { data, errors } = error;
      if (data && Object.keys(data).length !== 0 && errors) {
        const [key] = Object.keys(data);
        const flattenedResult = flattenItems(modelIntrospection, name, data[key]);
        if (flattenedResult) {
          if (options == null ? void 0 : options.selectionSet) {
            return { data: flattenedResult, errors };
          } else {
            const [initialized] = initializeModel(client, name, [flattenedResult], modelIntrospection, auth.authMode, auth.authToken, !!context);
            return { data: initialized, errors };
          }
        } else {
          return handleSingularGraphQlError(error);
        }
      } else {
        return handleSingularGraphQlError(error);
      }
    }
  });
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/operations/list.mjs
function listFactory(client, modelIntrospection, model, getInternals2, context = false, customUserAgentDetails) {
  const listWithContext = (contextSpec, args) => {
    return _list(client, modelIntrospection, model, getInternals2, args, contextSpec, customUserAgentDetails);
  };
  const list = (args) => {
    return _list(client, modelIntrospection, model, getInternals2, args, void 0, customUserAgentDetails);
  };
  return context ? listWithContext : list;
}
function _list(client, modelIntrospection, model, getInternals2, args, contextSpec, customUserAgentDetails) {
  return selfAwareAsync(async (resultPromise) => {
    var _a, _b, _c, _d;
    const { name } = model;
    const query = generateGraphQLDocument(modelIntrospection, model, "LIST", args);
    const variables = buildGraphQLVariables(model, "LIST", args, modelIntrospection);
    const auth = authModeParams(client, getInternals2, args);
    const headers = getCustomHeaders(client, getInternals2, args == null ? void 0 : args.headers);
    const userAgentOverride = createUserAgentOverride(customUserAgentDetails);
    try {
      const basePromise = contextSpec ? client.graphql(contextSpec, {
        ...auth,
        query,
        variables
      }, headers) : client.graphql({
        ...auth,
        query,
        variables,
        ...userAgentOverride
      }, headers);
      const extendedPromise = extendCancellability(basePromise, resultPromise);
      const { data, extensions } = await extendedPromise;
      if (data !== void 0) {
        const [key] = Object.keys(data);
        if (data[key].items) {
          const flattenedResult = data[key].items.map((value) => flattenItems(modelIntrospection, name, value));
          if (args == null ? void 0 : args.selectionSet) {
            return {
              data: flattenedResult,
              nextToken: data[key].nextToken,
              extensions
            };
          } else {
            const initialized = initializeModel(client, name, flattenedResult, modelIntrospection, auth.authMode, auth.authToken, !!contextSpec);
            return {
              data: initialized,
              nextToken: data[key].nextToken,
              extensions
            };
          }
        }
        return {
          data: data[key],
          nextToken: data[key].nextToken,
          extensions
        };
      }
    } catch (error) {
      const { data, errors } = error;
      if (data !== void 0 && data !== null && Object.keys(data).length !== 0 && errors) {
        const [key] = Object.keys(data);
        if ((_a = data[key]) == null ? void 0 : _a.items) {
          const flattenedResult = data[key].items.map((value) => flattenItems(modelIntrospection, name, value));
          if (flattenedResult) {
            if (args == null ? void 0 : args.selectionSet) {
              return {
                data: flattenedResult,
                nextToken: (_b = data[key]) == null ? void 0 : _b.nextToken,
                errors
              };
            } else {
              const initialized = initializeModel(client, name, flattenedResult, modelIntrospection, auth.authMode, auth.authToken, !!contextSpec);
              return {
                data: initialized,
                nextToken: (_c = data[key]) == null ? void 0 : _c.nextToken,
                errors
              };
            }
          }
          return {
            data: data[key],
            nextToken: (_d = data[key]) == null ? void 0 : _d.nextToken,
            errors
          };
        } else {
          return handleListGraphQlError(error);
        }
      } else {
        return handleListGraphQlError(error);
      }
    }
  });
}

// node_modules/@smithy/util-base64/dist-es/constants.browser.js
var alphabetByEncoding = {};
var alphabetByValue = new Array(64);
for (let i = 0, start = "A".charCodeAt(0), limit = "Z".charCodeAt(0); i + start <= limit; i++) {
  const char = String.fromCharCode(i + start);
  alphabetByEncoding[char] = i;
  alphabetByValue[i] = char;
}
for (let i = 0, start = "a".charCodeAt(0), limit = "z".charCodeAt(0); i + start <= limit; i++) {
  const char = String.fromCharCode(i + start);
  const index = i + 26;
  alphabetByEncoding[char] = index;
  alphabetByValue[index] = char;
}
for (let i = 0; i < 10; i++) {
  alphabetByEncoding[i.toString(10)] = i + 52;
  const char = i.toString(10);
  const index = i + 52;
  alphabetByEncoding[char] = index;
  alphabetByValue[index] = char;
}
alphabetByEncoding["+"] = 62;
alphabetByValue[62] = "+";
alphabetByEncoding["/"] = 63;
alphabetByValue[63] = "/";
var bitsPerLetter = 6;
var bitsPerByte = 8;
var maxLetterValue = 63;

// node_modules/@smithy/util-base64/dist-es/fromBase64.browser.js
var fromBase64 = (input) => {
  let totalByteLength = input.length / 4 * 3;
  if (input.slice(-2) === "==") {
    totalByteLength -= 2;
  } else if (input.slice(-1) === "=") {
    totalByteLength--;
  }
  const out = new ArrayBuffer(totalByteLength);
  const dataView = new DataView(out);
  for (let i = 0; i < input.length; i += 4) {
    let bits = 0;
    let bitLength = 0;
    for (let j = i, limit = i + 3; j <= limit; j++) {
      if (input[j] !== "=") {
        if (!(input[j] in alphabetByEncoding)) {
          throw new TypeError(`Invalid character ${input[j]} in base64 string.`);
        }
        bits |= alphabetByEncoding[input[j]] << (limit - j) * bitsPerLetter;
        bitLength += bitsPerLetter;
      } else {
        bits >>= bitsPerLetter;
      }
    }
    const chunkOffset = i / 4 * 3;
    bits >>= bitLength % bitsPerByte;
    const byteLength = Math.floor(bitLength / bitsPerByte);
    for (let k = 0; k < byteLength; k++) {
      const offset = (byteLength - k - 1) * bitsPerByte;
      dataView.setUint8(chunkOffset + k, (bits & 255 << offset) >> offset);
    }
  }
  return new Uint8Array(out);
};

// node_modules/@smithy/util-base64/node_modules/@smithy/util-utf8/dist-es/fromUtf8.browser.js
var fromUtf8 = (input) => new TextEncoder().encode(input);

// node_modules/@smithy/util-base64/dist-es/toBase64.browser.js
function toBase64(_input) {
  let input;
  if (typeof _input === "string") {
    input = fromUtf8(_input);
  } else {
    input = _input;
  }
  const isArrayLike = typeof input === "object" && typeof input.length === "number";
  const isUint8Array = typeof input === "object" && typeof input.byteOffset === "number" && typeof input.byteLength === "number";
  if (!isArrayLike && !isUint8Array) {
    throw new Error("@smithy/util-base64: toBase64 encoder function only accepts string | Uint8Array.");
  }
  let str = "";
  for (let i = 0; i < input.length; i += 3) {
    let bits = 0;
    let bitLength = 0;
    for (let j = i, limit = Math.min(i + 3, input.length); j < limit; j++) {
      bits |= input[j] << (limit - j - 1) * bitsPerByte;
      bitLength += bitsPerByte;
    }
    const bitClusterCount = Math.ceil(bitLength / bitsPerLetter);
    bits <<= bitClusterCount * bitsPerLetter - bitLength;
    for (let k = 1; k <= bitClusterCount; k++) {
      const offset = (bitClusterCount - k) * bitsPerLetter;
      str += alphabetByValue[(bits & maxLetterValue << offset) >> offset];
    }
    str += "==".slice(0, 4 - bitClusterCount);
  }
  return str;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/conversationMessageDeserializers.mjs
var deserializeContent = (content) => content.map((block2) => {
  if (block2.image) {
    return deserializeImageBlock(block2);
  }
  if (block2.document) {
    return deserializeDocumentBlock(block2);
  }
  if (block2.toolUse) {
    return deserializeToolUseBlock(block2);
  }
  if (block2.toolResult) {
    return deserializeToolResultBlock(block2);
  }
  return removeNullsFromBlock(block2);
});
var deserializeImageBlock = ({ image }) => ({
  image: {
    ...image,
    source: {
      ...image.source,
      bytes: fromBase64(image.source.bytes)
    }
  }
});
var deserializeDocumentBlock = ({ document }) => ({
  document: {
    ...document,
    source: {
      ...document.source,
      bytes: fromBase64(document.source.bytes)
    }
  }
});
var deserializeJsonBlock = ({ json }) => ({
  json: JSON.parse(json)
});
var deserializeToolUseBlock = ({ toolUse }) => ({
  toolUse: {
    ...toolUse,
    input: JSON.parse(toolUse.input)
  }
});
var deserializeToolResultBlock = ({ toolResult }) => ({
  toolResult: {
    toolUseId: toolResult.toolUseId,
    content: toolResult.content.map((toolResultBlock) => {
      if (toolResultBlock.image) {
        return deserializeImageBlock(toolResultBlock);
      }
      if (toolResultBlock.json) {
        return deserializeJsonBlock(toolResultBlock);
      }
      return removeNullsFromBlock(toolResultBlock);
    })
  }
});
var removeNullsFromBlock = (block2) => Object.fromEntries(Object.entries(block2).filter(([_, v]) => v !== null));

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/convertItemToConversationMessage.mjs
var convertItemToConversationMessage = ({ content, createdAt, id, conversationId, role }) => ({
  content: deserializeContent(content ?? []),
  conversationId,
  createdAt,
  id,
  role
});

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createListMessagesFunction.mjs
var createListMessagesFunction = (client, modelIntrospection, conversationId, conversationMessageModel, getInternals2) => async (input) => {
  const list = listFactory(client, modelIntrospection, conversationMessageModel, getInternals2, false, getCustomUserAgentDetails(AiAction.ListMessages));
  const { data, nextToken, errors } = await list({
    ...input,
    filter: { conversationId: { eq: conversationId } }
  });
  return {
    data: data.map((item) => convertItemToConversationMessage(item)),
    nextToken,
    errors
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/conversationStreamEventDeserializers.mjs
var convertItemToConversationStreamEvent = ({ id, conversationId, associatedUserMessageId, contentBlockIndex, contentBlockDoneAtIndex, contentBlockDeltaIndex, contentBlockText, contentBlockToolUse, stopReason, errors }) => {
  if (errors) {
    const error = {
      id,
      conversationId,
      associatedUserMessageId,
      errors
    };
    return { error };
  }
  const next = removeNullsFromConversationStreamEvent({
    id,
    conversationId,
    associatedUserMessageId,
    contentBlockIndex,
    contentBlockDoneAtIndex,
    contentBlockDeltaIndex,
    text: contentBlockText,
    toolUse: deserializeToolUseBlock2(contentBlockToolUse),
    stopReason
  });
  return { next };
};
var deserializeToolUseBlock2 = (contentBlockToolUse) => {
  if (contentBlockToolUse) {
    const toolUseBlock = {
      ...contentBlockToolUse,
      input: JSON.parse(contentBlockToolUse.input)
    };
    return toolUseBlock;
  }
};
var removeNullsFromConversationStreamEvent = (block2) => Object.fromEntries(Object.entries(block2).filter(([_, v]) => v !== null));

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createOnStreamEventFunction.mjs
var createOnStreamEventFunction = (client, modelIntrospection, conversationId, conversationRouteName, getInternals2) => (handler) => {
  const { conversations } = modelIntrospection;
  if (!conversations) {
    return {};
  }
  const subscribeSchema = conversations[conversationRouteName].message.subscribe;
  const subscribeOperation = customOpFactory(client, modelIntrospection, "subscription", subscribeSchema, false, getInternals2, getCustomUserAgentDetails(AiAction.OnStreamEvent));
  return subscribeOperation({ conversationId }).subscribe((data) => {
    const { next, error } = convertItemToConversationStreamEvent(data);
    if (error)
      handler.error(error);
    if (next)
      handler.next(next);
  });
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/conversationMessageSerializers.mjs
var serializeAiContext = (aiContext) => JSON.stringify(aiContext);
var serializeContent = (content) => content.map((block2) => {
  if (block2.image) {
    return serializeImageBlock(block2);
  }
  if (block2.document) {
    return serializeDocumentBlock(block2);
  }
  if (block2.toolResult) {
    return serializeToolResultBlock(block2);
  }
  return block2;
});
var serializeToolConfiguration = ({ tools }) => ({
  tools: Object.entries(tools).map(([name, tool]) => ({
    toolSpec: {
      name,
      description: tool.description,
      inputSchema: {
        json: JSON.stringify(tool.inputSchema.json)
      }
    }
  }))
});
var serializeImageBlock = ({ image }) => ({
  image: {
    ...image,
    source: {
      ...image.source,
      bytes: toBase64(image.source.bytes)
    }
  }
});
var serializeDocumentBlock = ({ document }) => ({
  document: {
    ...document,
    source: {
      ...document.source,
      bytes: toBase64(document.source.bytes)
    }
  }
});
var serializeJsonBlock = ({ json }) => ({
  json: JSON.stringify(json)
});
var serializeToolResultBlock = ({ toolResult }) => ({
  toolResult: {
    ...toolResult,
    content: toolResult.content.map((toolResultBlock) => {
      if (toolResultBlock.image) {
        return serializeImageBlock(toolResultBlock);
      }
      if (toolResultBlock.json) {
        return serializeJsonBlock(toolResultBlock);
      }
      return toolResultBlock;
    })
  }
});

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createSendMessageFunction.mjs
var createSendMessageFunction = (client, modelIntrospection, conversationId, conversationRouteName, getInternals2) => async (input) => {
  const { conversations } = modelIntrospection;
  if (!conversations) {
    return {};
  }
  const processedInput = typeof input === "string" ? { content: [{ text: input }] } : input;
  const { content, aiContext, toolConfiguration } = processedInput;
  const sendSchema = conversations[conversationRouteName].message.send;
  const sendOperation = customOpFactory(client, modelIntrospection, "mutation", sendSchema, false, getInternals2, getCustomUserAgentDetails(AiAction.SendMessage));
  const { data, errors } = await sendOperation({
    conversationId,
    content: serializeContent(content),
    ...aiContext && { aiContext: serializeAiContext(aiContext) },
    ...toolConfiguration && {
      toolConfiguration: serializeToolConfiguration(toolConfiguration)
    }
  });
  return {
    data: data ? convertItemToConversationMessage(data) : data,
    errors
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/convertItemToConversation.mjs
var convertItemToConversation = (client, modelIntrospection, conversationId, conversationCreatedAt, conversationUpdatedAt, conversationRouteName, conversationMessageModel, getInternals2, conversationMetadata, conversationName) => {
  if (!conversationId) {
    throw new Error(`An error occurred converting a ${conversationRouteName} conversation: Missing ID`);
  }
  return {
    id: conversationId,
    createdAt: conversationCreatedAt,
    updatedAt: conversationUpdatedAt,
    metadata: conversationMetadata,
    name: conversationName,
    onStreamEvent: createOnStreamEventFunction(client, modelIntrospection, conversationId, conversationRouteName, getInternals2),
    sendMessage: createSendMessageFunction(client, modelIntrospection, conversationId, conversationRouteName, getInternals2),
    listMessages: createListMessagesFunction(client, modelIntrospection, conversationId, conversationMessageModel, getInternals2)
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createCreateConversationFunction.mjs
var createCreateConversationFunction = (client, modelIntrospection, conversationRouteName, conversationModel, conversationMessageModel, getInternals2) => async (input) => {
  const { name, metadata: metadataObject } = input ?? {};
  const metadata = JSON.stringify(metadataObject);
  const createOperation = getFactory(client, modelIntrospection, conversationModel, "CREATE", getInternals2, false, getCustomUserAgentDetails(AiAction.CreateConversation));
  const { data, errors } = await createOperation({ name, metadata });
  return {
    data: convertItemToConversation(client, modelIntrospection, data == null ? void 0 : data.id, data == null ? void 0 : data.createdAt, data == null ? void 0 : data.updatedAt, conversationRouteName, conversationMessageModel, getInternals2, data == null ? void 0 : data.metadata, data == null ? void 0 : data.name),
    errors
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createGetConversationFunction.mjs
var createGetConversationFunction = (client, modelIntrospection, conversationRouteName, conversationModel, conversationMessageModel, getInternals2) => async ({ id }) => {
  const get5 = getFactory(client, modelIntrospection, conversationModel, "GET", getInternals2, false, getCustomUserAgentDetails(AiAction.GetConversation));
  const { data, errors } = await get5({ id });
  return {
    data: data ? convertItemToConversation(client, modelIntrospection, data.id, data.createdAt, data.updatedAt, conversationRouteName, conversationMessageModel, getInternals2, data == null ? void 0 : data.metadata, data == null ? void 0 : data.name) : data,
    errors
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createListConversationsFunction.mjs
var createListConversationsFunction = (client, modelIntrospection, conversationRouteName, conversationModel, conversationMessageModel, getInternals2) => async (input) => {
  const list = listFactory(client, modelIntrospection, conversationModel, getInternals2, false, getCustomUserAgentDetails(AiAction.ListConversations));
  const { data, nextToken, errors } = await list(input);
  return {
    data: data.map((datum) => {
      return convertItemToConversation(client, modelIntrospection, datum.id, datum.createdAt, datum.updatedAt, conversationRouteName, conversationMessageModel, getInternals2, datum == null ? void 0 : datum.metadata, datum == null ? void 0 : datum.name);
    }),
    nextToken,
    errors
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createDeleteConversationFunction.mjs
var createDeleteConversationFunction = (client, modelIntrospection, conversationRouteName, conversationModel, conversationMessageModel, getInternals2) => async ({ id }) => {
  const deleteOperation = getFactory(client, modelIntrospection, conversationModel, "DELETE", getInternals2, false, getCustomUserAgentDetails(AiAction.DeleteConversation));
  const { data, errors } = await deleteOperation({ id });
  return {
    data: data ? convertItemToConversation(client, modelIntrospection, data == null ? void 0 : data.id, data == null ? void 0 : data.createdAt, data == null ? void 0 : data.updatedAt, conversationRouteName, conversationMessageModel, getInternals2, data == null ? void 0 : data.metadata, data == null ? void 0 : data.name) : data,
    errors
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/ai/createUpdateConversationFunction.mjs
var createUpdateConversationFunction = (client, modelIntrospection, conversationRouteName, conversationModel, conversationMessageModel, getInternals2) => async ({ id, metadata: metadataObject, name }) => {
  const metadata = JSON.stringify(metadataObject);
  const updateOperation = getFactory(client, modelIntrospection, conversationModel, "UPDATE", getInternals2, false, getCustomUserAgentDetails(AiAction.UpdateConversation));
  const { data, errors } = await updateOperation({ id, metadata, name });
  return {
    data: data ? convertItemToConversation(client, modelIntrospection, data == null ? void 0 : data.id, data == null ? void 0 : data.createdAt, data == null ? void 0 : data.updatedAt, conversationRouteName, conversationMessageModel, getInternals2, data == null ? void 0 : data.metadata, data == null ? void 0 : data.name) : data,
    errors
  };
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/utils/clientProperties/generateConversationsProperty.mjs
function generateConversationsProperty(client, apiGraphQLConfig, getInternals2) {
  const modelIntrospection = apiGraphQLConfig == null ? void 0 : apiGraphQLConfig.modelIntrospection;
  if (!(modelIntrospection == null ? void 0 : modelIntrospection.conversations)) {
    return {};
  }
  const conversations = {};
  for (const { name, conversation, message, models, nonModels, enums } of Object.values(modelIntrospection.conversations)) {
    const conversationModel = models[conversation.modelName];
    const conversationMessageModel = models[message.modelName];
    if (!conversationModel || !conversationMessageModel) {
      return {};
    }
    const conversationModelIntrospection = {
      ...modelIntrospection,
      models: {
        ...modelIntrospection.models,
        ...models
      },
      nonModels: {
        ...modelIntrospection.nonModels,
        ...nonModels
      },
      enums: {
        ...modelIntrospection.enums,
        ...enums
      }
    };
    conversations[name] = {
      update: createUpdateConversationFunction(client, conversationModelIntrospection, name, conversationModel, conversationMessageModel, getInternals2),
      create: createCreateConversationFunction(client, conversationModelIntrospection, name, conversationModel, conversationMessageModel, getInternals2),
      get: createGetConversationFunction(client, conversationModelIntrospection, name, conversationModel, conversationMessageModel, getInternals2),
      delete: createDeleteConversationFunction(client, conversationModelIntrospection, name, conversationModel, conversationMessageModel, getInternals2),
      list: createListConversationsFunction(client, conversationModelIntrospection, name, conversationModel, conversationMessageModel, getInternals2)
    };
  }
  return conversations;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/utils/clientProperties/generateGenerationsProperty.mjs
function generateGenerationsProperty(client, apiGraphQLConfig, getInternals2) {
  const modelIntrospection = apiGraphQLConfig == null ? void 0 : apiGraphQLConfig.modelIntrospection;
  if (!(modelIntrospection == null ? void 0 : modelIntrospection.generations)) {
    return {};
  }
  const generations = {};
  for (const generation of Object.values(modelIntrospection.generations)) {
    generations[generation.name] = customOpFactory(client, modelIntrospection, "query", generation, false, getInternals2, getCustomUserAgentDetails(AiAction.Generation));
  }
  return generations;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/utils/clientProperties/generateEnumsProperty.mjs
var generateEnumsProperty = (graphqlConfig) => {
  const modelIntrospection = graphqlConfig.modelIntrospection;
  if (!modelIntrospection) {
    return {};
  }
  const enums = {};
  for (const [_, enumData] of Object.entries(modelIntrospection.enums)) {
    enums[enumData.name] = {
      values: () => enumData.values
    };
  }
  return enums;
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/operations/indexQuery.mjs
function indexQueryFactory(client, modelIntrospection, model, indexMeta, getInternals2, context = false) {
  const indexQueryWithContext = (contextSpec, args, options) => {
    return _indexQuery(client, modelIntrospection, model, indexMeta, getInternals2, {
      ...args,
      ...options
    }, contextSpec);
  };
  const indexQuery = (args, options) => {
    return _indexQuery(client, modelIntrospection, model, indexMeta, getInternals2, {
      ...args,
      ...options
    });
  };
  return context ? indexQueryWithContext : indexQuery;
}
function processGraphQlResponse(modelIntroSchema, modelName, result, selectionSet, modelInitializer) {
  const { data, extensions } = result;
  const [key] = Object.keys(data);
  if (data[key].items) {
    const flattenedResult = data[key].items.map((value) => flattenItems(modelIntroSchema, modelName, value));
    return {
      data: selectionSet ? flattenedResult : modelInitializer(flattenedResult),
      nextToken: data[key].nextToken,
      extensions
    };
  }
  return {
    data: data[key],
    nextToken: data[key].nextToken,
    extensions
  };
}
function _indexQuery(client, modelIntrospection, model, indexMeta, getInternals2, args, contextSpec) {
  return selfAwareAsync(async (resultPromise) => {
    var _a, _b, _c, _d;
    const { name } = model;
    const query = generateGraphQLDocument(modelIntrospection, model, "INDEX_QUERY", args, indexMeta);
    const variables = buildGraphQLVariables(model, "INDEX_QUERY", args, modelIntrospection, indexMeta);
    const auth = authModeParams(client, getInternals2, args);
    const modelInitializer = (flattenedResult) => initializeModel(client, name, flattenedResult, modelIntrospection, auth.authMode, auth.authToken, !!contextSpec);
    try {
      const headers = getCustomHeaders(client, getInternals2, args == null ? void 0 : args.headers);
      const graphQlParams = {
        ...auth,
        query,
        variables
      };
      const requestArgs = [graphQlParams, headers];
      if (contextSpec !== void 0) {
        requestArgs.unshift(contextSpec);
      }
      const basePromise = client.graphql(...requestArgs);
      const extendedPromise = extendCancellability(basePromise, resultPromise);
      const response = await extendedPromise;
      if (response.data !== void 0) {
        return processGraphQlResponse(modelIntrospection, name, response, args == null ? void 0 : args.selectionSet, modelInitializer);
      }
    } catch (error) {
      const { data, errors } = error;
      if (data !== void 0 && data !== null && Object.keys(data).length !== 0 && errors) {
        const [key] = Object.keys(data);
        if ((_a = data[key]) == null ? void 0 : _a.items) {
          const flattenedResult = (_b = data[key]) == null ? void 0 : _b.items.map((value) => flattenItems(modelIntrospection, name, value));
          if (flattenedResult) {
            return {
              data: (args == null ? void 0 : args.selectionSet) ? flattenedResult : modelInitializer(flattenedResult),
              nextToken: (_c = data[key]) == null ? void 0 : _c.nextToken
            };
          }
        }
        return {
          data: data[key],
          nextToken: (_d = data[key]) == null ? void 0 : _d.nextToken
        };
      } else {
        return handleListGraphQlError(error);
      }
    }
  });
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/operations/subscription.mjs
function subscriptionFactory(client, modelIntrospection, model, operation, getInternals2) {
  const { name } = model;
  const subscription = (args) => {
    const query = generateGraphQLDocument(modelIntrospection, model, operation, args);
    const variables = buildGraphQLVariables(model, operation, args, modelIntrospection);
    const auth = authModeParams(client, getInternals2, args);
    const headers = getCustomHeaders(client, getInternals2, args == null ? void 0 : args.headers);
    const observable = client.graphql({
      ...auth,
      query,
      variables
    }, headers);
    return observable.pipe(map((value) => {
      const [key] = Object.keys(value.data);
      const data = value.data[key];
      const flattenedResult = flattenItems(modelIntrospection, name, data);
      if (flattenedResult === null) {
        return null;
      } else if (args == null ? void 0 : args.selectionSet) {
        return flattenedResult;
      } else {
        const [initialized] = initializeModel(client, name, [flattenedResult], modelIntrospection, auth.authMode, auth.authToken);
        return initialized;
      }
    }));
  };
  return subscription;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/utils/resolvePKFields.mjs
function resolvePKFields(model) {
  const { primaryKeyFieldName, sortKeyFieldNames } = model.primaryKeyInfo;
  return [primaryKeyFieldName, ...sortKeyFieldNames];
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/utils/findIndexByFields.mjs
function findIndexByFields(needle, haystack, keyFields) {
  const searchObject = Object.fromEntries(keyFields.map((fieldName) => [fieldName, needle[fieldName]]));
  for (let i = 0; i < haystack.length; i++) {
    if (Object.keys(searchObject).every((k) => searchObject[k] === haystack[i][k])) {
      return i;
    }
  }
  return -1;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/operations/observeQuery.mjs
function observeQueryFactory(models, model) {
  const { name } = model;
  const observeQuery = (arg) => new Observable((subscriber) => {
    const items = [];
    const messageQueue = [];
    let receiveMessages = (...messages) => {
      return messageQueue.push(...messages);
    };
    const onCreateSub = models[name].onCreate(arg).subscribe({
      next(item) {
        receiveMessages({ item, type: "create" });
      },
      error(error) {
        subscriber.error({ type: "onCreate", error });
      }
    });
    const onUpdateSub = models[name].onUpdate(arg).subscribe({
      next(item) {
        receiveMessages({ item, type: "update" });
      },
      error(error) {
        subscriber.error({ type: "onUpdate", error });
      }
    });
    const onDeleteSub = models[name].onDelete(arg).subscribe({
      next(item) {
        receiveMessages({ item, type: "delete" });
      },
      error(error) {
        subscriber.error({ type: "onDelete", error });
      }
    });
    function ingestMessages(messages) {
      for (const message of messages) {
        const idx = findIndexByFields(message.item, items, pkFields);
        switch (message.type) {
          case "create":
            if (idx < 0)
              items.push(message.item);
            break;
          case "update":
            if (idx >= 0)
              items[idx] = message.item;
            break;
          case "delete":
            if (idx >= 0)
              items.splice(idx, 1);
            break;
          default:
            console.error("Unrecognized message in observeQuery.", message);
        }
      }
      subscriber.next({
        items,
        isSynced: true
      });
    }
    const pkFields = resolvePKFields(model);
    (async () => {
      let firstPage = true;
      let nextToken = null;
      while (!subscriber.closed && (firstPage || nextToken)) {
        firstPage = false;
        const { data: page, errors, nextToken: _nextToken } = await models[name].list({ ...arg, nextToken });
        nextToken = _nextToken;
        items.push(...page);
        const isSynced = messageQueue.length === 0 && (nextToken === null || nextToken === void 0);
        subscriber.next({
          items,
          isSynced
        });
        if (Array.isArray(errors)) {
          for (const error of errors) {
            subscriber.error(error);
          }
        }
      }
      if (messageQueue.length > 0) {
        ingestMessages(messageQueue);
      }
      receiveMessages = (...messages) => {
        ingestMessages(messages);
        return items.length;
      };
    })();
    return () => {
      onCreateSub.unsubscribe();
      onUpdateSub.unsubscribe();
      onDeleteSub.unsubscribe();
    };
  });
  return observeQuery;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/clientUtils.mjs
var attributeIsSecondaryIndex = (attr) => {
  var _a, _b, _c;
  return attr.type === "key" && // presence of `name` property distinguishes GSI from primary index
  ((_a = attr.properties) == null ? void 0 : _a.name) && ((_b = attr.properties) == null ? void 0 : _b.queryField) && ((_c = attr.properties) == null ? void 0 : _c.fields.length) > 0;
};
var getSecondaryIndexesFromSchemaModel = (model) => {
  var _a;
  const idxs = (_a = model.attributes) == null ? void 0 : _a.filter(attributeIsSecondaryIndex).map((attr) => {
    const queryField = attr.properties.queryField;
    const [pk, ...sk] = attr.properties.fields;
    return {
      queryField,
      pk,
      sk
    };
  });
  return idxs || [];
};
var excludeDisabledOps = (mis, modelName) => {
  var _a;
  const modelAttrs = (_a = mis.models[modelName].attributes) == null ? void 0 : _a.find((attr) => attr.type === "model");
  const coarseToFineDict = {
    queries: ["list", "get", "observeQuery"],
    mutations: ["create", "update", "delete"],
    subscriptions: ["onCreate", "onUpdate", "onDelete"]
  };
  const disabledOps = [];
  if (!modelAttrs) {
    return graphQLOperationsInfo;
  }
  if (modelAttrs.properties) {
    for (const [key, value] of Object.entries(modelAttrs.properties)) {
      if (!(key in coarseToFineDict)) {
        continue;
      }
      if (value === null) {
        disabledOps.push(...coarseToFineDict[key]);
      } else if (value instanceof Object) {
        disabledOps.push(...Object.keys(value));
      }
    }
  }
  if (disabledOps.includes("list")) {
    disabledOps.push("observeQuery");
  }
  const disabledOpsUpper = disabledOps.map((op) => op.toUpperCase());
  const filteredGraphQLOperations = Object.fromEntries(Object.entries(graphQLOperationsInfo).filter(([key]) => !disabledOpsUpper.includes(key)));
  return filteredGraphQLOperations;
};

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/internals/utils/clientProperties/generateModelsProperty.mjs
function generateModelsProperty(client, apiGraphQLConfig, getInternals2) {
  const models = {};
  const modelIntrospection = apiGraphQLConfig.modelIntrospection;
  if (!modelIntrospection) {
    return {};
  }
  const SUBSCRIPTION_OPS = ["ONCREATE", "ONUPDATE", "ONDELETE"];
  for (const model of Object.values(modelIntrospection.models)) {
    const { name } = model;
    models[name] = {};
    const enabledModelOps = excludeDisabledOps(modelIntrospection, name);
    Object.entries(enabledModelOps).forEach(([key, { operationPrefix }]) => {
      const operation = key;
      if (operation === "LIST") {
        models[name][operationPrefix] = listFactory(client, modelIntrospection, model, getInternals2);
      } else if (SUBSCRIPTION_OPS.includes(operation)) {
        models[name][operationPrefix] = subscriptionFactory(client, modelIntrospection, model, operation, getInternals2);
      } else if (operation === "OBSERVEQUERY") {
        models[name][operationPrefix] = observeQueryFactory(models, model);
      } else {
        models[name][operationPrefix] = getFactory(client, modelIntrospection, model, operation, getInternals2);
      }
    });
    const secondaryIdxs = getSecondaryIndexesFromSchemaModel(model);
    for (const idx of secondaryIdxs) {
      models[name][idx.queryField] = indexQueryFactory(client, modelIntrospection, model, idx, getInternals2);
    }
  }
  return models;
}

// node_modules/@aws-amplify/data-schema/dist/esm/runtime/addSchemaToClient.mjs
function addSchemaToClient(client, apiGraphqlConfig, getInternals2) {
  upgradeClientCancellation(client);
  client.models = generateModelsProperty(client, apiGraphqlConfig, getInternals2);
  client.enums = generateEnumsProperty(apiGraphqlConfig);
  client.queries = generateCustomQueriesProperty(client, apiGraphqlConfig, getInternals2);
  client.mutations = generateCustomMutationsProperty(client, apiGraphqlConfig, getInternals2);
  client.subscriptions = generateCustomSubscriptionsProperty(client, apiGraphqlConfig, getInternals2);
  client.conversations = generateConversationsProperty(client, apiGraphqlConfig, getInternals2);
  client.generations = generateGenerationsProperty(client, apiGraphqlConfig, getInternals2);
  return client;
}

// node_modules/@aws-amplify/api-graphql/dist/esm/GraphQLAPI.mjs
function isGraphQLOptionsWithOverride(options) {
  return INTERNAL_USER_AGENT_OVERRIDE in options;
}
var GraphQLAPIClass = class extends InternalGraphQLAPIClass {
  getModuleName() {
    return "GraphQLAPI";
  }
  /**
   * Executes a GraphQL operation
   *
   * @param options - GraphQL Options
   * @param [additionalHeaders] - headers to merge in after any `libraryConfigHeaders` set in the config
   * @returns An Observable if the query is a subscription query, else a promise of the graphql result.
   */
  graphql(amplify, options, additionalHeaders) {
    const userAgentDetails = {
      category: Category.API,
      action: ApiAction.GraphQl
    };
    if (isGraphQLOptionsWithOverride(options)) {
      const { [INTERNAL_USER_AGENT_OVERRIDE]: internalUserAgentOverride, ...cleanOptions } = options;
      return super.graphql(amplify, cleanOptions, additionalHeaders, {
        ...userAgentDetails,
        ...internalUserAgentOverride
      });
    }
    return super.graphql(amplify, options, additionalHeaders, {
      ...userAgentDetails
    });
  }
  /**
   * Checks to see if an error thrown is from an api request cancellation
   * @param error - Any error
   * @returns A boolean indicating if the error was from an api request cancellation
   */
  isCancelError(error) {
    return super.isCancelError(error);
  }
  /**
   * Cancels an inflight request. Only applicable for graphql queries and mutations
   * @param {any} request - request to cancel
   * @returns A boolean indicating if the request was cancelled
   */
  cancel(request, message) {
    return super.cancel(request, message);
  }
};
var GraphQLAPI = new GraphQLAPIClass();

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/v6.mjs
function graphql2(options, additionalHeaders) {
  const internals = getInternals(this);
  const clientEndpoint = internals.endpoint;
  const clientAuthMode = internals.authMode;
  const clientApiKey = internals.apiKey;
  options.authMode = options.authMode || clientAuthMode;
  options.apiKey = options.apiKey ?? clientApiKey;
  options.authToken = options.authToken || internals.authToken;
  if (clientEndpoint && options.authMode === "apiKey" && !options.apiKey) {
    throw new Error("graphql() requires an explicit `apiKey` for a custom `endpoint` when `authMode = 'apiKey'`.");
  }
  const headers = additionalHeaders || internals.headers;
  const result = GraphQLAPI.graphql(
    // TODO: move V6Client back into this package?
    internals.amplify,
    {
      ...options,
      endpoint: clientEndpoint
    },
    headers
  );
  return result;
}
function cancel2(promise, message) {
  return GraphQLAPI.cancel(promise, message);
}
function isCancelError2(error) {
  return GraphQLAPI.isCancelError(error);
}

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/utils/runtimeTypeGuards/isApiGraphQLProviderConfig.mjs
function isApiGraphQLConfig2(apiGraphQLConfig) {
  return apiGraphQLConfig !== void 0;
}

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/utils/runtimeTypeGuards/isConfigureEventWithResourceConfig.mjs
function isConfigureEventWithResourceConfig(payload) {
  return payload.event === "configure";
}

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/generateClient.mjs
function generateClient(params) {
  var _a;
  const client = {
    [__amplify]: params.amplify,
    [__authMode]: params.authMode,
    [__authToken]: params.authToken,
    [__apiKey]: "apiKey" in params ? params.apiKey : void 0,
    [__endpoint]: "endpoint" in params ? params.endpoint : void 0,
    [__headers]: params.headers,
    graphql: graphql2,
    cancel: cancel2,
    isCancelError: isCancelError2,
    models: emptyProperty,
    enums: emptyProperty,
    queries: emptyProperty,
    mutations: emptyProperty,
    subscriptions: emptyProperty
  };
  const apiGraphqlConfig = (_a = params.amplify.getConfig().API) == null ? void 0 : _a.GraphQL;
  if (client[__endpoint]) {
    if (!client[__authMode]) {
      throw new Error("generateClient() requires an explicit `authMode` when `endpoint` is provided.");
    }
    if (client[__authMode] === "apiKey" && !client[__apiKey]) {
      throw new Error("generateClient() requires an explicit `apiKey` when `endpoint` is provided and `authMode = 'apiKey'`.");
    }
  }
  if (!client[__endpoint]) {
    if (isApiGraphQLConfig2(apiGraphqlConfig)) {
      addSchemaToClient(client, apiGraphqlConfig, getInternals);
    } else {
      generateModelsPropertyOnAmplifyConfigure(client);
    }
  }
  return client;
}
var generateModelsPropertyOnAmplifyConfigure = (clientRef) => {
  Hub.listen("core", (coreEvent) => {
    var _a;
    if (!isConfigureEventWithResourceConfig(coreEvent.payload)) {
      return;
    }
    const apiGraphQLConfig = (_a = coreEvent.payload.data.API) == null ? void 0 : _a.GraphQL;
    if (isApiGraphQLConfig2(apiGraphQLConfig)) {
      addSchemaToClient(clientRef, apiGraphQLConfig, getInternals);
    }
  });
};
var emptyProperty = new Proxy({}, {
  get() {
    throw new Error("Client could not be generated. This is likely due to `Amplify.configure()` not being called prior to `generateClient()` or because the configuration passed to `Amplify.configure()` is missing GraphQL provider configuration.");
  }
});

// node_modules/@aws-amplify/api/dist/esm/API.mjs
function generateClient2(options) {
  return generateClient({
    ...options || {},
    amplify: Amplify
  });
}

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/events/index.mjs
var events_exports = {};
__export(events_exports, {
  closeAll: () => closeAll,
  connect: () => connect,
  post: () => post4
});

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/events/utils.mjs
var normalizeAuth = (explicitAuthMode, defaultAuthMode) => {
  if (!explicitAuthMode) {
    return defaultAuthMode;
  }
  if (explicitAuthMode === "identityPool") {
    return "iam";
  }
  return explicitAuthMode;
};
var configure = () => {
  var _a;
  const config = Amplify.getConfig();
  const eventsConfig = (_a = config.API) == null ? void 0 : _a.Events;
  if (!eventsConfig) {
    throw new Error("Amplify configuration is missing. Have you called Amplify.configure()?");
  }
  const configAuthMode = normalizeAuth(eventsConfig.defaultAuthMode, "apiKey");
  const options = {
    appSyncGraphqlEndpoint: eventsConfig.endpoint,
    region: eventsConfig.region,
    authenticationType: configAuthMode,
    apiKey: eventsConfig.apiKey
  };
  return options;
};
var serializeEvents = (events) => {
  if (Array.isArray(events)) {
    return events.map((ev, idx) => {
      const eventJson2 = JSON.stringify(ev);
      if (eventJson2 === void 0) {
        throw new Error(`Event must be a valid JSON value. Received ${ev} at index ${idx}`);
      }
      return eventJson2;
    });
  }
  const eventJson = JSON.stringify(events);
  if (eventJson === void 0) {
    throw new Error(`Event must be a valid JSON value. Received ${events}`);
  }
  return [eventJson];
};

// node_modules/@aws-amplify/api-graphql/dist/esm/Providers/AWSAppSyncEventsProvider/index.mjs
var PROVIDER_NAME2 = "AWSAppSyncEventsProvider";
var WS_PROTOCOL_NAME2 = "aws-appsync-event-ws";
var CONNECT_URI2 = "";
var AWSAppSyncEventProvider = class extends AWSWebSocketProvider {
  constructor() {
    super({
      providerName: PROVIDER_NAME2,
      wsProtocolName: WS_PROTOCOL_NAME2,
      connectUri: CONNECT_URI2
    });
    this.allowNoSubscriptions = true;
  }
  getProviderName() {
    return PROVIDER_NAME2;
  }
  async connect(options) {
    return super.connect(options);
  }
  subscribe(options, customUserAgentDetails) {
    return super.subscribe(options, customUserAgentDetails).pipe();
  }
  async publish(options, customUserAgentDetails) {
    return super.publish(options, customUserAgentDetails);
  }
  closeIfNoActiveSubscription() {
    this._closeSocketIfRequired();
  }
  async _prepareSubscriptionPayload({ options, subscriptionId, customUserAgentDetails, additionalCustomHeaders, libraryConfigHeaders, publish }) {
    const { appSyncGraphqlEndpoint, authenticationType, query, apiKey, region, variables } = options;
    const data = {
      channel: query,
      events: variables !== void 0 ? serializeEvents(variables) : void 0
    };
    const serializedData = JSON.stringify(data);
    const headers = {
      ...await awsRealTimeHeaderBasedAuth({
        apiKey,
        appSyncGraphqlEndpoint,
        authenticationType,
        payload: serializedData,
        canonicalUri: "",
        region,
        additionalCustomHeaders
      }),
      ...libraryConfigHeaders,
      ...additionalCustomHeaders,
      [USER_AGENT_HEADER]: getAmplifyUserAgent(customUserAgentDetails)
    };
    const subscriptionMessage = {
      id: subscriptionId,
      channel: query,
      events: variables !== void 0 ? serializeEvents(variables) : void 0,
      authorization: {
        ...headers
      },
      payload: {
        events: variables !== void 0 ? serializeEvents(variables) : void 0,
        channel: query,
        extensions: {
          authorization: {
            ...headers
          }
        }
      },
      type: publish ? MESSAGE_TYPES.EVENT_PUBLISH : MESSAGE_TYPES.EVENT_SUBSCRIBE
    };
    const serializedSubscriptionMessage = JSON.stringify(subscriptionMessage);
    return serializedSubscriptionMessage;
  }
  _handleSubscriptionData(message) {
    this.logger.debug(`subscription message from AWS AppSync Events: ${message.data}`);
    const { id = "", event: payload, type } = JSON.parse(String(message.data));
    const { observer = null, query = "", variables = {} } = this.subscriptionObserverMap.get(id) || {};
    this.logger.debug({ id, observer, query, variables });
    if (type === MESSAGE_TYPES.DATA && payload) {
      const deserializedEvent = JSON.parse(payload);
      if (observer) {
        observer.next({ id, type, event: deserializedEvent });
      } else {
        this.logger.debug(`observer not found for id: ${id}`);
      }
      return [true, { id, type, payload: deserializedEvent }];
    }
    return [false, { id, type, payload }];
  }
  _unsubscribeMessage(subscriptionId) {
    return {
      id: subscriptionId,
      type: MESSAGE_TYPES.EVENT_STOP
    };
  }
  _extractConnectionTimeout(data) {
    const { connectionTimeoutMs = DEFAULT_KEEP_ALIVE_TIMEOUT } = data;
    return connectionTimeoutMs;
  }
  _extractErrorCodeAndType(data) {
    const { errors: [{ errorType = "", errorCode = 0 } = {}] = [] } = data;
    return { errorCode, errorType };
  }
};
var AppSyncEventProvider = new AWSAppSyncEventProvider();

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/events/appsyncRequest.mjs
var USER_AGENT_HEADER3 = "x-amz-user-agent";
async function appsyncRequest(amplify, options, additionalHeaders = {}, abortController, customUserAgentDetails) {
  const { region, appSyncGraphqlEndpoint: endpoint, authenticationType: authMode, query, variables } = options;
  if (!endpoint) {
    throw new Error("No endpoint");
  }
  const { withCredentials } = resolveLibraryOptions2(amplify);
  const headers = await requestHeaders(amplify, options, additionalHeaders, customUserAgentDetails);
  const body = {
    channel: query,
    events: variables
  };
  const signingServiceInfo = ["apiKey", "none"].includes(authMode) ? void 0 : {
    service: "appsync",
    region
  };
  const { body: responseBody } = await post3(amplify, {
    url: new AmplifyUrl(endpoint),
    options: {
      headers,
      body,
      signingServiceInfo,
      withCredentials
    },
    abortController
  });
  const response = await responseBody.json();
  if (isGraphQLResponseWithErrors(response)) {
    throw repackageUnauthorizedError(response);
  }
  return response;
}
async function requestHeaders(amplify, options, additionalHeaders, customUserAgentDetails) {
  const { apiKey, appSyncGraphqlEndpoint: endpoint, authenticationType: authMode, query, variables, authToken } = options;
  const { headers: customHeadersFn } = resolveLibraryOptions2(amplify);
  let additionalCustomHeaders;
  if (typeof additionalHeaders === "function") {
    const requestOptions = {
      method: "POST",
      url: new AmplifyUrl(endpoint).toString(),
      queryString: query
    };
    additionalCustomHeaders = await additionalHeaders(requestOptions);
  } else {
    additionalCustomHeaders = additionalHeaders;
  }
  if (authToken) {
    additionalCustomHeaders = {
      ...additionalCustomHeaders,
      Authorization: authToken
    };
  }
  const authHeaders = await headerBasedAuth(amplify, authMode, apiKey, additionalCustomHeaders);
  const customHeaders = customHeadersFn && await customHeadersFn({
    query,
    variables
  });
  const headers = {
    ...authHeaders,
    // Custom headers included in Amplify configuration options:
    ...customHeaders,
    // Custom headers from individual requests or API client configuration:
    ...additionalCustomHeaders,
    // User agent headers:
    [USER_AGENT_HEADER3]: getAmplifyUserAgent(customUserAgentDetails)
  };
  return headers;
}

// node_modules/@aws-amplify/api-graphql/dist/esm/internals/events/index.mjs
var openChannels = /* @__PURE__ */ new Set();
async function connect(channel, options) {
  const providerOptions = configure();
  providerOptions.authenticationType = normalizeAuth(options == null ? void 0 : options.authMode, providerOptions.authenticationType);
  providerOptions.apiKey = (options == null ? void 0 : options.apiKey) || providerOptions.apiKey;
  providerOptions.authToken = (options == null ? void 0 : options.authToken) || providerOptions.authToken;
  await AppSyncEventProvider.connect(providerOptions);
  const channelId = amplifyUuid();
  openChannels.add(channelId);
  let _subscription;
  const sub = (observer, subOptions) => {
    if (!openChannels.has(channelId)) {
      throw new Error("Channel is closed");
    }
    const subscribeOptions = { ...providerOptions, query: channel };
    subscribeOptions.authenticationType = normalizeAuth(subOptions == null ? void 0 : subOptions.authMode, subscribeOptions.authenticationType);
    subscribeOptions.apiKey = (subOptions == null ? void 0 : subOptions.apiKey) || subscribeOptions.apiKey;
    subscribeOptions.authToken = (subOptions == null ? void 0 : subOptions.authToken) || subscribeOptions.authToken;
    _subscription = AppSyncEventProvider.subscribe(subscribeOptions).subscribe(observer);
    return _subscription;
  };
  const pub = async (event, pubOptions) => {
    if (!openChannels.has(channelId)) {
      throw new Error("Channel is closed");
    }
    const publishOptions = {
      ...providerOptions,
      query: channel,
      variables: event
    };
    publishOptions.authenticationType = normalizeAuth(pubOptions == null ? void 0 : pubOptions.authMode, publishOptions.authenticationType);
    publishOptions.apiKey = (pubOptions == null ? void 0 : pubOptions.apiKey) || publishOptions.apiKey;
    publishOptions.authToken = (pubOptions == null ? void 0 : pubOptions.authToken) || publishOptions.authToken;
    return AppSyncEventProvider.publish(publishOptions);
  };
  const close = async () => {
    _subscription && _subscription.unsubscribe();
    openChannels.delete(channelId);
    setTimeout(() => {
      if (openChannels.size === 0) {
        AppSyncEventProvider.closeIfNoActiveSubscription();
      }
    }, 1e3);
  };
  return {
    subscribe: sub,
    close,
    publish: pub
  };
}
async function post4(channel, event, options) {
  var _a;
  const providerOptions = configure();
  providerOptions.authenticationType = normalizeAuth(options == null ? void 0 : options.authMode, providerOptions.authenticationType);
  providerOptions.apiKey = (options == null ? void 0 : options.apiKey) || providerOptions.apiKey;
  providerOptions.authToken = (options == null ? void 0 : options.authToken) || providerOptions.authToken;
  const normalizedChannelName = channel[0] === "/" ? channel : `/${channel}`;
  const publishOptions = {
    ...providerOptions,
    query: normalizedChannelName,
    variables: serializeEvents(event)
  };
  const abortController = new AbortController();
  const res = await appsyncRequest(Amplify, publishOptions, {}, abortController);
  if (((_a = res.failed) == null ? void 0 : _a.length) > 0) {
    return res.failed;
  }
}
async function closeAll() {
  await AppSyncEventProvider.close();
}
export {
  ApiError,
  CONNECTION_STATE_CHANGE,
  ConnectionState,
  GraphQLAuthError,
  del2 as del,
  events_exports as events,
  generateClient2 as generateClient,
  get4 as get,
  head2 as head,
  isCancelError,
  patch2 as patch,
  post2 as post,
  put2 as put
};
//# sourceMappingURL=aws-amplify_data.js.map
