Feature: Framing QA

  Scenario: Studs are pine IfcBeams
    Given the model
    Then every beam named "Stud" has material "Pine"
    And every beam named "Stud" has ifc type "IfcBeam"
    And every beam named "Stud" has width 80
