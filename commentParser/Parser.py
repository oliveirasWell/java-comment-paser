from entities.Class import Class
from entities.Comment import Comment
from entities.Attribute import Attribute
from entities.Method import Method
from commentParser.Scanner import Scanner


class Parser:
    def __init__(self, file_path, verbose):
        self.elements = []
        self.classes = []
        self.methods = []
        self.comments = []
        self.actual_class_stack = []
        self.actual_method_stack = []
        self.access_control_modifiers_stack = []
        self.non_access_control_modifiers_stack = []
        self.all_elements = []
        self.lambdaMethodStack = []
        self.filePath = file_path
        self.brace_count = 0
        self.documentation = True
        self.method_started = False
        self.brace_count_when_method_started = -1
        self.brace_count_when_enum_item_started = -1
        self.declarationStarted = False
        self.lambdaMethodStarted = False
        self.isEnumDeclaration = False
        self.inEnumBody = False
        self.elementItemInEnumBody = None
        self.scanner = Scanner(self.filePath)
        self.verbose = verbose

    def resolveComment(self, actual_class_stack, actual_method_stack, all_elements, comments, documentation, method_started, scanner,
                       element_item_in_enum_body=None):
        comment_item = {}
        is_doc = documentation
        class_name = (actual_class_stack[-1]).className if len(actual_class_stack) else None
        method_name = (actual_method_stack[-1]).methodName if method_started else None
        element_item_in_enum_body = element_item_in_enum_body.attributeName if element_item_in_enum_body is not None else None

        if scanner.actual_token == '//':
            comment_content = []
            while scanner.actual_token != '\n' and scanner.actual_token is not None:
                comment_content.append(scanner.actual_token)
                scanner.getNextToken()

            comment_item = Comment('//', comment_content, scanner.actual_line, scanner.actual_line, isLicenca=is_doc, className=class_name,
                                   methodName=method_name, fieldName=element_item_in_enum_body)

        if scanner.actual_token == '/*':
            line_start = scanner.actual_line
            comment_content = [scanner.actual_token]

            while scanner.actual_token != '*/' and scanner.actual_token is not None:
                scanner.getNextToken()
                comment_content.append(scanner.actual_token)

            comment_item = Comment('/*', comment_content, line_start, scanner.actual_line, isLicenca=is_doc, className=class_name, methodName=method_name,
                                   fieldName=element_item_in_enum_body)

        if comment_item:
            all_elements.append(comment_item)
            comments.append(comment_item)

    def matchCommentsAndElements(self, allElements):

        comments_message = ""

        for i in range(len(allElements)):

            element = allElements[i]

            if type(element) is Comment:

                nextElement = allElements[i + 1] if i + 1 < len(allElements) else None
                prevElement = allElements[i - 1] if i - 1 > 0 else None

                if nextElement and element.className is None and type(nextElement) is Class and not element.isLicenca:
                    element.className = nextElement.className
                elif nextElement and element.className is not None and type(nextElement) is Class and nextElement.isEnum:
                    element.className = nextElement.className
                elif prevElement and element.fieldName is None and element.methodName is None and type(
                        prevElement) is Attribute and element.lineStart == prevElement.lineStart:
                    element.fieldName = prevElement.attributeName
                elif nextElement and element.fieldName is None and element.methodName is None and type(nextElement) is Attribute:
                    element.fieldName = nextElement.attributeName
                elif prevElement and element.fieldName is None and element.methodName is None and type(
                        prevElement) is Method and element.lineStart == prevElement.lineStart:
                    element.methodName = prevElement.methodName
                elif nextElement and element.fieldName is None and element.methodName is None and type(nextElement) is Method:
                    element.methodName = nextElement.methodName

                comments_message = comments_message + element.print()

        return comments_message

    def parse(self):

        self.brace_count = 0
        self.documentation = True
        self.method_started = False
        self.brace_count_when_method_started = -1
        self.brace_count_when_enum_item_started = -1
        self.declarationStarted = False
        self.lambdaMethodStarted = False
        self.isEnumDeclaration = False
        self.inEnumBody = False
        self.elementItemInEnumBody = None

        while self.scanner.getNextToken():

            if self.verbose:
                print("{} -- {}".format(self.scanner.actual_line, self.scanner.actual_token))

            if (self.method_started or self.lambdaMethodStarted) and self.scanner.actual_token not in ['//', '/*', '{', '}', None]:
                continue

            if '{' in self.scanner.actual_token:
                self.brace_count = self.brace_count + 1
                continue

            if '}' in self.scanner.actual_token:
                if self.method_started and self.brace_count_when_method_started == self.brace_count:
                    method = self.actual_method_stack.pop()
                    method.lineEnd = self.scanner.actual_line
                    self.methods.append(method)
                    self.method_started = False
                    self.brace_count_when_method_started = -1

                elif self.inEnumBody and self.brace_count_when_enum_item_started == self.brace_count:
                    self.brace_count_when_enum_item_started = -1
                    self.inEnumBody = False
                    self.elementItemInEnumBody = None
                    if self.scanner.getToken(self.scanner.actual_position + 1) == ';':
                        self.isEnumDeclaration = False

                elif self.lambdaMethodStarted and self.brace_count == (self.lambdaMethodStack[-1])['self.brace_count']:
                    self.lambdaMethodStack.pop()
                    if len(self.lambdaMethodStack) == 0:
                        self.lambdaMethodStarted = False

                elif self.brace_count == len(self.actual_class_stack):
                    classItem = self.actual_class_stack.pop()
                    classItem.lineEnd = self.scanner.actual_line
                    self.classes.append(classItem)

                self.brace_count = self.brace_count - 1
                continue

            if self.isEnumDeclaration and not self.inEnumBody:
                while self.scanner.actual_token == '//' or self.scanner.actual_token == '/*' or self.scanner.actual_token == '\n':
                    self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                        self.method_started,
                                        self.scanner,
                                        self.elementItemInEnumBody)
                    self.scanner.getNextToken()

                if self.scanner.actual_token == ',':
                    continue

                elementItem = Attribute(self.scanner.actual_token, self.scanner.actual_token, self.scanner.actual_line)
                self.elements.append(elementItem)
                self.all_elements.append(elementItem)
                self.scanner.getNextToken()

                if self.scanner.actual_token == '(':
                    # Get conteudo dentro dos parenteses
                    contParenteses = 0
                    while self.scanner.actual_token != ')' and contParenteses != 0:
                        if self.scanner.actual_token == ')':
                            contParenteses = contParenteses - 1

                        if self.scanner.actual_token == '(':
                            contParenteses = contParenteses + 1

                        if self.scanner.actual_token == '/*':
                            self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                                self.method_started, self.scanner,
                                                self.elementItemInEnumBody)

                        self.scanner.getNextToken()

                if self.scanner.actual_token == '{':
                    self.inEnumBody = True
                    self.elementItemInEnumBody = elementItem
                    brace_count_when_enum_item_started = self.brace_count + 1
                    self.scanner.setPosition(self.scanner.actual_position - 1)
                continue

            if self.scanner.actual_token == '->':
                if self.scanner.getToken(self.scanner.actual_position + 1) == '{':
                    lambdaMethodStarted = True
                    self.lambdaMethodStack.append({'brace_count': self.brace_count + 1})
                continue

            if self.declarationStarted:
                while self.scanner.actual_token not in ['//', '/*', ';', '->']:
                    self.scanner.getNextToken()

                if self.scanner.actual_token == ';':
                    self.declarationStarted = False

                self.scanner.setPosition(self.scanner.actual_position - 1)
                continue

            if self.scanner.actual_token == '"':
                while self.scanner.actual_token != '"' and not (self.scanner.actual_token == '"' and self.scanner.getToken(self.scanner.actual_position - 1)):
                    self.scanner.getNextToken()
                continue

            if self.scanner.actual_token == 'do':
                continue

            if self.scanner.actual_token == 'new':
                continue

            if self.scanner.actual_token in ['while', 'if', 'for']:
                self.scanner.getNextToken()

                # Get conteudo dentro dos parenteses
                contParenteses = 0
                while self.scanner.actual_token != ')' and contParenteses != 0:

                    if self.scanner.actual_token == ')':
                        contParenteses = contParenteses - 1

                    if self.scanner.actual_token == '(':
                        contParenteses = contParenteses + 1

                    if self.scanner.actual_token == '/*':
                        self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                            self.method_started, self.scanner,
                                            self.elementItemInEnumBody)

                    self.scanner.getNextToken()

                continue

            if self.scanner.actual_token == 'package':
                self.documentation = False
                continue

            if self.scanner.actual_token == 'import':
                while self.scanner.actual_token != '\n':
                    if self.scanner.actual_token == '/*':
                        self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                            self.method_started, self.scanner,
                                            self.elementItemInEnumBody)
                    self.scanner.getNextToken()
                continue

            if self.scanner.actual_token == '\n':
                continue

            if self.scanner.actual_token == 'return':
                continue

            if self.scanner.actual_token[0] == '@':
                while self.scanner.actual_token != '\n':
                    if self.scanner.actual_token == '/*':
                        self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                            self.method_started, self.scanner,
                                            self.elementItemInEnumBody)
                    self.scanner.getNextToken()
                continue

            if self.scanner.actual_token in ['public', 'private', 'proteced']:
                self.access_control_modifiers_stack.append(self.scanner.actual_token)
                continue

            if self.scanner.actual_token in ['static', 'final', 'synchronized', 'volatile']:
                self.non_access_control_modifiers_stack.append(self.scanner.actual_token)
                continue

            # declaração de metodo ou elemento
            if self.scanner.actual_token or self.scanner.actual_token == 'void':
                if (';' in self.scanner.getToken(self.scanner.actual_position + 2) or (
                        '=' in self.scanner.getToken(self.scanner.actual_position + 2))) and not self.method_started:
                    elementType = self.scanner.actual_token
                    self.scanner.getNextToken()
                    element = self.scanner.actual_token
                    elementItem = Attribute(elementType, element, self.scanner.actual_line)
                    self.all_elements.append(elementItem)
                    self.elements.append(elementItem)

                    if '=' in [self.scanner.actual_token, self.scanner.getToken(self.scanner.actual_position + 1)]:
                        while self.scanner.actual_token not in [';', '->']:
                            if self.scanner.actual_token == '/*':
                                self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                                    self.method_started, self.scanner,
                                                    self.elementItemInEnumBody)
                            self.scanner.getNextToken()

                        if self.scanner.actual_token == '->':
                            self.declarationStarted = True
                            self.scanner.setPosition(self.scanner.actual_position - 1)

                    continue

                elif ('(' in self.scanner.getToken(self.scanner.actual_position + 3) or '(' in self.scanner.getToken(
                        self.scanner.actual_position + 2) or '(' in self.scanner.getToken(
                    self.scanner.actual_position + 1)) and not self.method_started:

                    isAbstract = 'abstract' in [self.scanner.getToken(self.scanner.actual_position - 1), self.scanner.actual_token]

                    methodName = self.scanner.actual_token
                    while ')' not in self.scanner.actual_token:
                        self.scanner.getNextToken()
                        if self.scanner.actual_token == '/*':
                            self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                                self.method_started, self.scanner,
                                                self.elementItemInEnumBody)
                        else:
                            methodName = methodName + ((" " + self.scanner.actual_token) if self.scanner.actual_token != '\n' else '')

                    methodItem = Method(methodName, self.scanner.actual_line)
                    self.actual_method_stack.append(methodItem)
                    self.all_elements.append(methodItem)

                    self.method_started = True if not isAbstract else False
                    self.brace_count_when_method_started = self.brace_count + 1 if not isAbstract else self.brace_count_when_method_started
                    continue

            if self.scanner.actual_token in ['class', 'enum']:
                classType = self.scanner.actual_token
                self.scanner.getNextToken()
                classItem = Class(classType, self.scanner.actual_token, self.scanner.actual_line)
                self.all_elements.append(classItem)
                self.actual_class_stack.append(classItem)

                if classType == 'enum':
                    self.isEnumDeclaration = True
                    self.inEnumBody = False

                continue

            if self.scanner.actual_token == '//' or self.scanner.actual_token == '/*':
                self.resolveComment(self.actual_class_stack, self.actual_method_stack, self.all_elements, self.comments, self.documentation,
                                    self.method_started,
                                    self.scanner, self.elementItemInEnumBody)
                continue

        self.__printAllElementsIn__()

        return self.matchCommentsAndElements(self.all_elements)

    def __printAllElementsIn__(self):
        elements = ""
        for element in self.all_elements:
            elements = elements + element.print()
        return elements
