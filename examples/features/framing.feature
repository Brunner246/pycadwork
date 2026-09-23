Feature: Framing QA

  Scenario: Pfosten are Duo I IfcBeams
    Given the model
    Then every beam named "Pfosten" has material "Duo I"
    And every beam named "Pfosten" has ifc type "IfcBeam"
    And every beam named "Pfosten" has width 60
