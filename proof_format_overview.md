# VeriPB Proof Format Overview

This document provides a brief overview of the formula and proof file formats supported by VeriPB. A full description of the VeriPB proof format version 3 grammar can be found in the [latest grammar document](https://gitlab.com/api/v4/projects/70013030/jobs/artifacts/main/raw/docs/grammar.pdf?job=build-grammar-doc&search_recent_successful_pipelines=true).

[[_TOC_]]

## Useful Examples

A good way to getting started is to have a look at the examples under
[`tests/instances/correct/`](https://gitlab.com/MIAOresearch/software/VeriPB/-/tree/main/tests/instances/correct/version3)
and to run VeriPB with the `--trace` option, which will trace the derived
constraints and checking process.

For example:

```bash
cd tests/instances/correct
veripb --trace version3/all_diff.opb version3/all_diff.pbp
```

## Supported Formula File Formats

### OPB

The standard format for the input formula is the
[OPB](https://www.cril.univ-artois.fr/PB24/OPBcompetition.pdf) format. A short overview
can be found
[here](https://gitlab.com/MIAOresearch/software/roundingsat/-/blob/master/InputFormats.md).

The verifier also supports some extensions to OPB, allowing arbitrary variable
names instead of `x1`, `x2`, ... Variable names must follow the following
properties:

- start with a letter in `A-Z, a-z` or an underscore
- are at least two characters long
- may not contain space

The following characters are guaranteed to be supported: `a-z, A-Z, 0-9,
[]{}_^-`. Support of further characters is implementation specific and VeriPB may give
an error if unsupported characters are used.

#### Reification Shorthands

As an additional extension to OPB, constraints may be written using reification
shorthands as syntactic sugar for standard PB inequalities:

```
z1 z2 ~z3 ==> +1 x1 +2 x2 >= 2;  % if z1 ∧ z2 ∧ ¬z3 then x1 + 2x2 ≥ 2
z1        <== +1 x1 +2 x2 >= 2;  % if x1 + 2x2 ≥ 2 then z1
```

The left implication (`<==`) requires exactly one literal on the left; the
right implication (`==>`) allows one or more. These are interpreted as standard PB 
inequalities and can be used anywhere an OPB-style constraint is expected.

### DIMACS CNF

An alternative format for the formula is the [DIMACS CNF
format](https://web.archive.org/web/20190325181937/https://www.satcompetition.org/2009/format-benchmarks2009.html).
This format is then internally viewed as a OPB formula.

#### Variables

The variable `i` in the DIMACS CNF format is represented by `x<i>` and the
literal `-i` is `~x<i>`.

#### Clauses

VeriPB follows the semantics of DIMACS CNF with respect to duplicate literals
in clauses. Hence, the clause `1 -2 1 0` becomes the constraint `1 x1 1 ~x2 >=
1 ;`.
Clauses containing opposing literals are normalized after deduplication so that all terms are over distinct literals.
For instance, the clause `1 1 2 -2 -1 3 0` becomes the constraint `1 x3 >= -1`.

### MaxSAT

Another alternative format is the 2022 version of the [MaxSAT
(WCNF)](https://maxsat-evaluations.github.io/2026/rules.html#input) format.
This format is again internally viewed
as an OPB formula.

#### Variables

The variable `i` in the WCNF format input file is represented by `x<i>`.

#### Hard Clauses

Hard clauses are viewed as OPB constraints, where all coefficients are `1` and
the right-hand side is `1`.

#### Soft Clauses

VeriPB will add soft clauses containing one literal directly to the objective
without adding a constraint to the database. This is achieved by adding the
negated literal with the weight of the soft clause as the coefficient to the
objective.

Soft clauses with more than one literal are reformulated using a blocking
literal `_b<i>`, where `i` is the index of the soft clause in the WCNF input
file. Then, the soft clauses with the literal `~_b<i>` is added to the OPB
formula as a constraint, and the literal `~_b<i>` with the weight of the soft
clause as coefficient is added to the objective.

#### Example

| WCNF        | OPB                              |
| ----------- | -------------------------------- |
|             | `min: 1 ~x1 1 ~_b3 2 ~x2 2 ~_b5` |
| `1 1 0`     |                                  |
| `h 1 2 3 0` | `1 x1 1 x2 1 x3 >= 1`            |
| `1 2 3 0`   | `1 x2 1 x3 1 ~_b3 >= 1`          |
| `2 2 0`     |                                  |
| `2 1 2 0`   | `1 x1 1 x2 1 ~_b5 >= 1`          |

## Basic Proof Format

### TLDR;

```
pseudo-Boolean proof version 3.0
% compute constraint in polish notation
pol <sequence of operations in reverse polish notation> ;
% introduce constraint that is verified by reverse unit propagation
rup  <OPB style constraint>;
% introduce constraint that is verified by reverse unit propagation with the given hints
rup  <OPB style constraint> : <ConstraintID1> <ConstraintID2> ... ;
```

### Introduction

VeriPB supports multiple rules, which are described in more detail below. Each
rule begins with a keyword and is terminated by a semicolon, and may create an
arbitrary number of constraints (including none). The verifier maintains a
database of constraints, and each constraint is assigned an index, called its
ConstraintID. These start from 1 and increase by 1 for every added constraint.
Rules can reference other constraints by their ConstraintID.

The constraints in the formula file are loaded before any rule is executed and
get the first ConstraintIDs. Within the database, constraints are always
considered to be either in the "core set" (consisting initially of the formula
constraints), or the "derived set" (populated by default with constraints added
due to derivation rules). Constraints may be deleted or moved from the derived
to the core set under certain conditions, detailed below.

In what follows, we will use IDmax to refer to the largest used ID before a
given rule is executed.

#### Constraint Labels

In addition to a ConstraintIDs, a label for a constraint can be explicitly
specified. The ConstraintID and the label can then be used interchangeably in
the proof. Labels must begin with the character `@`. A constraint in the OPB
file can be labelled by preceding the constraint definition by the label
identifier, e.g.

```
@label_name 1 x1 1 x2 1 x3 >= 1 ;
```

Constraints introduced by a rule can be labelled preceding the rule keyword by
the label identifier, e.g.

```
@label_name pol 1 2 + 3 d ;
```

If a constraint label is defined when it has already been defined earlier, the
label will be overwritten with the new ConstraintID.

Once defined, labels can be used anywhere a ConstraintID can be used. For
example, if constraint 2 is labelled `@label_name`, then one can write the previous rule as (see below
for pol syntax):

```
pol 1 @label_name + 3 d;
```

In the remainder of this document, whenever a ConstraintID is used as an
argument for a proof rule, it will be implicit that a label can be optionally
used instead of the ConstraintID.

### (pol) Reverse Polish Notation

```
pol <sequence of operations in reverse polish notation> ;
```

Adds a new constraint with ConstraintID := IDmax + 1. This constraint will be
the result of the given sequence of operations applied to the current
constraint database. The operations are based on cutting planes rules for
pseudo-Boolean inequalities, and are written down in reverse polish notation.
The sequence of operations must result in a stack with exactly one constraint
on it.

If we use `<constraint>` to denote either a ConstraintID or a subsequence in
reverse polish notation, we can specify the available operations as follows.

#### Addition

```
<constraint> <constraint> +
```

#### Scalar Multiplication

```
<constraint> <factor> *
```

The factor is a non-negative integer and must be the second operand.

#### Boolean Division

```
<constraint> <divisor> d
```

Divides the constraint in literal normal form (non-negative coefficients) by
the divisor.

The divisor is a strictly positive integer and must be the second operand.

Alternatively, the operation can specify division of the constraint in variable
normal form (non-negated variables) by using `c`

```
<constraint> <divisor> c
```

#### Boolean Saturation

```
<constraint> s
```

#### Literal Axioms

```
<literal>
```

Here `<literal>` is a variable name or its negation (`~`) and generates the
constraint that the literal is greater equal zero. For example, `~x1` will
generate the constraint `~x1 >= 0`.

#### Weakening

```
<constraint> <variable> w
```

Here `<variable>` is a variable name and must not be negated. This operation
adds sufficient literal axioms so that `<variable>` disappears from the
constraint, i.e., its coefficient becomes zero.

#### Reduce Right-hand Side

```
<constraint> <constant> -
```

This operation subtracts the given `<constant>` from the right-hand-side of the
constraint.

#### MIR Cuts

```
<constraint> <divisor> m
```

Apply MIR cut with the given `<divisor>` to the constraint in variable normal
form.

```
<constraint> <divisor> n
```

Apply MIR cut with the given `<divisor>` in literal normal form.


#### Summary of pol statements

This set of instructions allows writing down any treelike derivation with a
single rule.

For example

```
pol 42 3 * 43 + s 2 d;
```

Creates a new constraint by taking 3 times the constraint with index 42, then
adds constraint 43, followed by a saturation step and a division by 2.

### (rup) Reverse Unit Propagation

```
rup <OPB style constraint> ;
rup <OPB style constraint> : <ConstraintID1> <ConstraintID2> ... ;
```

Can be used as a convenient way to derive certain "obviously" implied
constraints. VeriPB will check a RUP step by temporarily adding the negation of
the constraint to the current database and performing unit propagation. If this
yields contradiction then the constraint is implied and can be added to the
database with ConstraintID := IdMax + 1, otherwise the proof will be rejected.

#### RUP Hints

Optionally, RUP rules can be annotated by a list of ConstraintIDs. If this list
is given, VeriPB will only perform unit propagation on the specified
constraints. The reserved symbol `~` is used to specify the negation of the
constraint to be derived. VeriPB will initially perform the unit propagation in
the order of the list. Hence, if the propagation order is known, then the
ConstraintIDs should be printed in order.


## Subproofs, Strengthening Rules and Order Definitions

The proof format also supports subproofs and strengthening rules to introduce
constraints that are not necessarily implied by the input formula.

### TLDR;

```
% add constraint with an explicit proof by contradiction
pbc <OPB-style constraint> : subproof
    <proof by contradiction derivation>
qed;

% add constraint by redundance-based strengthening
red <OPB style constraint> : <substitution> ;

% add constraint by redundance-based strengthening with subproof
red <OPB style constraint> : <substitution> : subproof
    proofgoal <goalID>
        <subproof derivation>
    qed;
    % More proof obligation derivations
    ...
    % Optional scoped derivations
    scope leq
        proofgoal <goalID>
            <subproof derivation>
        qed;
    end scope leq;
    % Optional scoped derivations
    scope geq
        proofgoal <goalID>
            <subproof derivation>
        qed;
    end scope geq;
qed;

% define preorder with specification
def_order <order name>
    vars
        left <list of variables> ;
        right <list of variables> ;
        aux <list of variables> ;
    end;

    spec
        <specification derivation>
    end spec;

    def
        <constraints defining the order>
    end;
    transitivity
        vars
            fresh_right <list of variables> ;
            fresh_aux_1 <list of variables> ;
            fresh_aux_2 <list of variables> ;
        end;
        proof
            <proofgoals>
        qed;
    end;

    reflexivity
        proof
            <proofgoals>
        qed;
    end;
end;
```

### (pbc) Proof by Contradiction
```
pbc <OPB style constraint>;
pbc <OPB style constraint> : subproof
    <proof by contradiction derivation>
qed;
```

Adding the constraint is successful if a contradiction can be derived from the
current database and the negation of the constraint. This requires a subproof
([see below](#Subproofs)) unless the constraint is a tautology (and hence its
negation is already a contradiction).

### Substitutions

A substitution `<substitution>` is a space-separated sequence of multiple
mappings from a variable to a constant or a literal.

```
<variable> -> 0
<variable> -> 1
<variable> -> <literal>
```

Using `->` is optional and can improve readability.

For example

```
x1 -> 0 x2 -> ~x3
x1 0 x2 ~x3
```

### (red) Redundance-Based Strengthening

```
red <OPB style constraint> : <substitution> ;
```

Adding the constraint is successful if it can be shown that every assignment
satisfying the constraints in the database $F$ but falsifying the to-be-added
constraint $C$ can be transformed into an assignment satisfying both by using
the witness substitution $\omega$. More formally it is checked that,

$$
F \land \neg C \models (F \land C)\upharpoonright\omega .
$$

For details, please refer to [[GN21](#references)].

If the redundance rule is used in the context of optimization and / or
dominance breaking, additional conditions are checked. For details, please
refer to [[BGMN23](#references)].

### Subproofs

For `pbc` and both strengthening rules it is possible to provide an explicit subproof to
demonstrate the required conditions. A subproof should be written after the
substitution in a strengthening step, beginning with `: subproof` and
concluding with `qed;`. Within a subproof it is possible to specify proof goals
for different obligatory derivations using `proofgoal <goalID>`, which are in
turn terminated by `qed;`. Each proofgoal must derive contradiction using the
provided constraints.

Example:

```
red 1 x1 >= 1 : x1 -> 1 : subproof
    proofgoal #1
        pol -1 -2 +;
    qed;

    proofgoal 1
        rup >= 1 ;
    qed;
qed;
```

Each `<goalID>` is determined as follows: if a goal originates from a
constraint in the database the `<goalID>` is identical to the ConstraintID of
the constraint in the database. Otherwise, the goalID begins with a `#`
followed by a number which is increased for each goal in the following order
(if applicable):
- the constraint to be derived (only redundance),
- one goal per constraint in the current pre-order (order definitions below),
- one goal for the negated pre-order (only dominance),
- objective condition (only for optimization problems).

Tip: Use the `--trace` option to display required goals.

#### Autoproving

For a subproof or a single proofgoal VeriPB will try some techniques to
automatically prove (_autoprove_) them. If VeriPB is able to do this, then it
is not required to present an explicit proof for the whole subproof or the
single proofgoal.

A subproof can be autoproven if unit propagation derives contradiction with
respect to the database and the additional premises added at the start of the
subproof (e.g., the negated constraint for [redundance-based
strengthening](#red-redundance-based-strengthening)).

A proofgoal can be autoproven if the goal constraint is trivial (degree of
falsity is non-positive), implied by [reverse unit propagation
(RUP)](#rup-reverse-unit-propagation), or [syntactically implied](#i-implies)
by any constraint in the database or the additional premise, where all
variables that are assigned by unit propagation are substituted with their
value in the premise and conclusion constraint of the implication.

Tip: We recommend that you look at the trace (using the `--trace` option) of
VeriPB to see what autoproving is done by VeriPB, and it can make sense to
compare the performance of autoproving and explicit proofs for your use case.


### (dom) Dominance Based Strengthening

```
dom <OPB style constraint> : <substitution> ;
```

For details, please refer to [[BGMN23](#references)]. For syntax have a look at
the example under
[`tests/instances/correct/version3/dominance_simple_order.pbp`](https://gitlab.com/MIAOresearch/software/veripb-dev/-/blob/main/tests/instances/correct/version3/dominance_simple_order.pbp).

Example proof:

```
% define a new order named "simple"
def_order simple
    vars
        % define "left" variables
        left u1;
        % define "right" variables
        % check |left| = |right|
        right v1;
        % define auxiliary variables
        % (the list of aux variables is empty)
        aux;
    end;

    % define the encoding
    def
        -1 u1 1 v1 >= 0;
    end;

    transitivity
        vars
            fresh_right w1;
        end;
        proof
            proofgoal #1
                pol -2 -3 + -1 +;
            qed : -1;
        qed;
    end;
end;

load_order simple x1;

dom 1 ~x1 1 x2 >= 1 : x1 -> x2 x2 -> x1 : subproof
%    proofgoal #1
%        p 14 15 +
%        c -1
%    qed
qed;
```

#### Order Definition

```
def_order <order name>
    vars
        left <list of variables> ;
        right <list of variables> ;
        aux <list of variables> ;
    end;

    spec
        <specification derivation>
    end spec;

    def
        <constraints defining the order>
    end;

    transitivity
        vars
            fresh_right <list of variables> ;
            fresh_aux_1 <list of variables> ;
            fresh_aux_2 <list of variables> ;
        end;
        proof
            <proofgoals>
        qed;
    end;

    reflexivity
        proof
            <proofgoals>
        qed;
    end;
end;
```

A new order ${\cal O}_\preceq(\vec{u}, \vec{v})$ (i.e., $\vec{u} \preceq
\vec{v}$) can be defined using the above syntax. The order must be a preorder,
thus the defined order must be reflexive and transitive.

The first `vars` defines the variables used in the definition of the order. The
variables after `left` are the variables in $\vec{u}$ and the variables after
`right` are the variables in $\vec{v}$. The number of variables in $\vec{u}$
must be the same as in $\vec{v}$. The variables after `aux` are additional
variables that can be used to define the order.

The constraints in `def` define the order. Only variables in `left`, `right`
and `aux` can be used.

The `transitivity` proof establishes that the order is transitive, i.e., if
${\cal O}_\preceq(\vec{u}, \vec{v})$ and ${\cal O}_\preceq(\vec{v}, \vec{w})$,
then ${\cal O}_\preceq(\vec{u}, \vec{w})$. The variables after `fresh_right`
are the variables in $\vec{w}$ and the number of variables in $\vec{w}$ has to
be the same as in $\vec{u}$ (and $\vec{v}$). In the `proof` it has to be proven
that each constraint in ${\cal O}_\preceq(\vec{u}, \vec{w})$ can be derived
from the constraints in ${\cal O}_\preceq(\vec{u}, \vec{v})$ and ${\cal
O}_\preceq(\vec{v}, \vec{w})$.

The `reflexivity` proof establishes that the order is reflexive, i.e., ${\cal
O}_\preceq(\vec{u}, \vec{u})$ is always satisfied. The `reflexivity` proof is optional if the
reflexivity of the order is trivial (negated constraints in ${\cal
O}_\preceq(\vec{u}, \vec{u})$ are contradiction). In the `proof` it has to be
proven that each constraint in ${\cal O}_\preceq(\vec{u}, \vec{u})$ can be
derived from an empty formula.

The transitivity proof must come before the reflexivity proof (if an explicit
reflexivity proof is given).

#### Specifications

Optionally, an auxiliary "specification" section may be provided that can derive
additional constraints on the variables of the order, including the auxiliary
variables, that may help to define it. This should be given after the variables
but before the order definition enclosed with `spec` and `end spec`.

For more details see [[ABB+26](#references)].

#### Scopes Inside Subproofs
When using an order that has a `spec` block (i.e., auxiliary variables), two
optional named scopes can appear inside a strengthening-rule subproof to
introduce the specification constraints as additional premises:

- **`scope leq`** introduces the constraints from
  $S_\preceq(\vec{z}{\upharpoonright}_\omega, \vec{z}, \vec{a})$ — the
  specification instantiated with the *witnessed* variables on the left. This
  scope may be used to prove all proof goals except the negated-order goal.
- **`scope geq`** introduces the constraints from $S_\preceq(\vec{z},
  \vec{z}{\upharpoonright}_\omega, \vec{a})$ — the specification instantiated
  with the *original* variables on the left. This scope is used exclusively to
  prove the negated-order proof goal (label `#N+1` for dominance).

Each scope may appear at most once per subproof, and they can occur in either
order. Constraints introduced inside a scope are only valid within that scope.

## Deletion and Non-Derivation Rules

### TLDR;
```
% delete constraints
del id <ConstraintID1> <ConstraintID2> <ConstraintID4> ... ;
del spec <OPB style constraint> ;
del range <ConstraintIDStart> <ConstraintIDEnd> ;
delc <ConstraintID1> <ConstraintID2> <ConstraintID3> ... ;
deld <ConstraintID1> <ConstraintID2> <ConstraintID3> ... ;

% objective update
obju <OPB style objective> ;

% moving constraints to core
core id <ConstraintID1> <ConstraintID2> ... ;
core range <ConstraintIDStart> <ConstraintIDEnd> ;
```

### (del) Delete Constraint

```
del id <ConstraintID1> <ConstraintID2> <ConstraintID3> ... ;
del spec <OPB style constraint> ;
del range <ConstraintIDStart> <ConstraintIDEnd> ;
```

Delete constraints with the given `ConstraintIDs` (`id`), or in the range from
`ConstraintIDStart` to `ConstraintIDEnd`, including `ConstraintIDStart` but not
`ConstraintIDEnd` (`range`), or which match a given OPB-style constraint (`spec`).

If a constraint is deleted that propagated under the empty assignment (e.g., a
unit clause), then the propagations from this constraint are also deleted from
the trail. This is different from the behaviour of the [DRAT proof
checker drat-trim](https://github.com/marijnheule/drat-trim).

#### Deletion from the Core Set

A constraint that is in the "core set" (see [[BGMN23](#references)] for
details) can only be deleted after a deletion check has been performed. This
deletion check comes in two flavours. By default, VeriPB runs [checked deletion
checks](#checked-deletion), as these guarantee that the new core set and the
input formula are equi-enumerable/equi-optimal/equisatisfiable. If a checked
deletion fails for any deletion from the core, these guarantees are lost and
VeriPB only performs [unchecked deletion checks](#unchecked-deletion) for the
remainder of the proof, since they never fail. However, VeriPB will still perform
checked deletion checks if core constraints are deleted while an order is loaded
or [strengthening-to-core](#strengthening-to-core-mode) is enabled while the derived set is not empty.

##### Unchecked Deletion

Unchecked deletion performs the following checks:

1. If **no** order is loaded and [strengthening-to-core](#strengthening-to-core-mode) is **disabled**, accept deletion.
2. Otherwise, if the derived set is empty, accept deletion.
3. Otherwise, unchecked deletion fails, and an error is reported.

##### Checked Deletion

The idea of checked deletion is to ensure that we can rederive the deleted
constraint from the remaining constraints in the core by [redundance-based
strengthening](#red-redundance-based-strengthening).

If deleting multiple constraints, they will be checked in the order they were
given. For instance, if we delete $C$ and $D$ and have the set of core
constraints $\mathcal{C}$, then it is first checked that $C$ can be derived
from $\mathcal{C} \setminus \{ C \}$ and then that $D$ can be derived from
$\mathcal{C} \setminus \{ C, D \}$.

The syntax for a deletion check is very similar to [redundance-based
strengthening](#red-redundance-based-strengthening). Checked deletion will
create the same proofgoals as redundance-based strengthening and a substitution
can be supplied if required to prove the proofgoals.
If an order is loaded or [strengthening-to-core](#strengthening-to-core-mode) is enabled, then the substitution has to be empty (i.e., trivial).

The following syntax is used for checked deletion with a witness:

```
<deletion rule> <deletion parameters> : <substitution> ;
```

The syntax of `<substitution>` is described in the [substitution
section](#substitution).

The proofgoals of checked deletion can be manually proven using the
[subproof](#subproofs) syntax, or they are [autoproven](#autoproving) by VeriPB
if they are trivial enough.

### (delc) Delete Core Constraint

```
delc <ConstraintID1> <ConstraintID2> <ConstraintID3> ... ;
```

This rule is identical to [`del id`](#delete-constraint) except that it checks
if all `ConstraintIDs` are from the core set. So the rule will fail if at least
one `ConstraintID` is from the derived set.

### (deld) Delete Derived Constraint

```
deld <ConstraintID1> <ConstraintID2> <ConstraintID3> ... ;
```

This rule is identical to [`del id`](#delete-constraint) except that it checks
if all `ConstraintIDs` are from the derived set. So the rule will fail if at
least one `ConstraintID` is from the core set.

### (obju) Objective Update

```
% objective update to new objective
obju new <new objective f_new in OPB format> ;
% objective update by difference
obju diff <f_new - f_old in OPB format> ;
% or with explicit subproof
obju new <new objective f_new in OPB format> : subproof
    proofgoal #1
        % proof f_new >= f_current
        <subproof>
    qed;
    proofgoal #2
        % proof f_current >= f_new
        <subproof>
    qed;
qed;
```

The version `obju new` of the rule updates the objective to the specified
objective.

The version `obju diff` updates the objective by adding the specified
difference $f_{new} - f_{current}$ between new objective $f_{new}$ and current objective $f_{current}$ to the current objective. Subtracting the
old objective from the new objective results in an affine function, like all
objective functions. Hence, the same syntax is used for stating a difference or
an objective.

The new objective will be the only valid objective after the update.

To update the objective, it has to be shown that the previous objective
($f_{current}$) is equal to the new objective ($f_{new}$). This is done by
showing that the constraints $f_{new} \geq f_{current}$ and $f_{current} \geq
f_{new}$ can be derived from the formula. If these two constraints can be
trivially proven by [autoproving](#autoproving), then no subproofs have to be
specified to derive these two constraints. Otherwise, subproofs have to be
specified for the constraints. The proofgoal ID for the constraint $f_{new}
\geq f_{current}$ is `#1` and for the constraint $f_{current} \geq f_{new}$ the
proofgoal ID is `#2`.

**Attention:** To maintain soundness, [autoproving](#autoproving) and subproofs
can only use constraints from the core set. Technically, this condition is not
necessary for deriving $f_{current} \geq f_{new}$ (proofgoal `#2`), but for
simplicity, this condition is required for the derivation of both constraints.


### Moving Constraints to Core

```
core id <ConstraintID1> <ConstraintID2> ... ;
core range <ConstraintIDStart> <ConstraintIDEnd> ;
```

Move the constraint with the given `ConstraintIDs` to the core set (`id`) or move the constraints in the range from
`ConstraintIDStart` to `ConstraintIDEnd`, including `ConstraintIDStart` but not
`ConstraintIDEnd` to the core set (`range`).

## Output and Conclusion Section

### TLDR;

```
% output section
output <output guarantee> <output type> ;
% conclusion section
conclusion <conclusion type> [<conclusion parameters>] ;
% end of proof
end pseudo-Boolean proof ;
```

Every proof has to end with the output and conclusion section. This section
must contain in the following order:

1. the output section
2. the conclusion section
3. end of proof

### Output Section

```
output <output guarantee> <output type> ;
```

For the moment, the output guarantees `NONE`, `DERIVABLE`, `EQUIENUMERABLE`, `EQUISATISFIABLE`,
and `EQUIOPTIMAL` and output types `IMPLICIT`, and `FILE` are implemented.

#### Output Guarantees

The following table details the output guarantees and what is required for the
guarantees. We refer to _input_ as the input problem that the proof starts with
and _output_ as the output problem to check against.

| Identifier        | Guarantee                                                      | Conditions                                                                                                               |
| ----------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `NONE`            | no guarantee                                                   | output type is empty (just `output NONE`)                                                                                |
| `DERIVABLE`       | _output_ derivable from _input_                                | no conditions                                                                                                            |
| `EQUISATISFIABLE` | _output_ is equisatisfiable to _input_                         | always checked deletion used, _input_ does not have objective                                                            |
| `EQUIOPTIMAL`     | _output_ has same optimal value as _input_                     | always checked deletion used, _input_ has objective                                                                      |
| `EQUIENUMERABLE`  | _output_ has the same number of (optimal) solutions as _input_ | always checked deletion used, no preserved variable in the domain of a witness if witnessing is used, no solution logged |

#### Output Types

The following table details the output types and how the output problem should be given.

| Identifier                          | How to give output?                                                                                                           |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `FILE`                              | external file in same format as input file gives as third positional argument (e.g., `veripb input.opb proof.pbp output.opb`) |
| `IMPLICIT`                          | output is implicitly the current core (and objective)                                                                         |
| `PERMUTATION`                       | constraints are permuted as given by a list of constraint IDs and current objective output                                    |

### Conclusion Section

```
conclusion NONE ;

conclusion SAT [: <literal> <literal> ...] ;
conclusion UNSAT [: <ConstraintID>] ;

conclusion BOUNDS <lower bound> [: <ConstraintID>] <upper bound> [: <literal> <literal> ...] ;
```

#### Conclusion `NONE`

The conclusion `NONE` states that the proof concludes without any conclusion.
This conclusion is always valid, but no guarantees on the proof are enforced.

#### Conclusion `SAT`

The conclusion `SAT` states that the formula is satisfiable. If this conclusion
is used, then the proof has to show that there exists at least one solution. To
show this, a list of literals can be specified after the conclusion, which must
be a solution with respect to the original problem. If no solution is specified after the conclusion, then at least
one solution has to be logged using log [(sol)ution](#sol-log-solution).

#### Conclusion `UNSAT`

The conclusion `UNSAT` states that the formula is unsatisfiable. If the proof
claims this conclusion then it has to show that contradiction can be derived.
This can be done by explicitly deriving contradiction and pointing to it as the
optional hint after the conclusion. If no hint is given, then there must be a
constraint in the database that syntactically implies contradiction.

#### Conclusion `BOUNDS`

This conclusion can only be used for optimization problems. The conclusion
`BOUNDS` states that the optimal value is between `<lower bound>` and `<upper
bound>`. If the bounds are equal, this means that the optimal value has been
found.

To show the correctness of the `<lower bound>` a constraint $C$ that shows that
the objective is at least the `<lower bound>` has to be derived. This has to be
done by explicitly deriving a constraint that syntactically implies $C$ (which
might already be derived in the proof). The ID of the constraint that
syntactically implies $C$ can optionally be given as a hint for the lower bound
or VeriPB will search through the database for this constraint.


To show the correctness of the `<upper bound>`, there must be a solution that
has an objective value that is at least as good as the `<upper bound>`. The
solution can be given as a hint, where the solution is evaluated with respect to the original problem, or otherwise must have been logged before in
the proof using the log [(sol)ution](#sol-log-solution) rule.

For optimization problems there are the following special cases:

**Infeasible:** Use the lower bound and upper bound to `INF` (infinity) to
denote an infeasible instance. The hint for the lower bound should be a
contradicting constraint and no hint is required for the upper bound.

**Unbounded:** This case does not really exist for PB instances, so you would
give the smallest possible value as lower bound and upper bound. No hint is
required for the lower bound and the hint for the upper bound is an assignment
that sets all literals in the objective to 0.

**Only lower bound:** The upper bound should be set to `INF`. No hint is
required for the upper bound.

#### Conclusion `ENUMERATION_COMPLETE` and `ENUMERATION_PARTIAL`

Two additional conclusion types are supported for enumeration problems 
```
conclusion ENUMERATION_COMPLETE <n> : <ConstraintID> ;
conclusion ENUMERATION_PARTIAL <n> ;
```

`ENUMERATION_COMPLETE n : i` states that exactly `n` projected solutions have
been witnessed via `solx`, and that constraint `i` is a contradiction
(establishing there are no further solutions).

`ENUMERATION_PARTIAL n` states that at least `n` projected solutions have been
witnessed, without claiming completeness.

### End of Proof

```
end pseudo-Boolean proof ;
```

The proof must end with this line. Everything after this line is not part of
this proof. In the future it will be possible to start a new proof after this.

## Convenience Rules and Rules for Sanity Checks

### TLDR;

```
% check number of constraints in formula
f <nProblemConstraints> ;
% check equality (note: ea was removed in 3.0; use @label e <constraint> instead)
e <OPB style constraint> : [<ConstraintID>] ;
% Check equality objective
eobj <OPB style objective> ;
% check a defined order matches expected
eord_def ...
% check the currently loaded order and variables 
eord_loaded <order name> <vars>;                 
% check that no order is currently loaded
eord_loaded;                                      
% check syntactic implication
i <OPB style constraint> : [<ConstraintID>] ;
% add constraint if syntactically implied
ia <OPB style constraint> : [<ConstraintID>] ;
% set level (for easier deletion) ;
setlvl <level> ;
% wipe out level (for easier deletion)
wiplvl <level> ;
% strengthening to core mode
strengthening_to_core on|off ;
```

### (f) Formula Check

```
f <nProblemConstraints> ;
```

This rule can be used to check that the correct number of constraints have been
loaded by VeriPB and to check that the proof logger starts with the correct
constraint ID.

The value of `<nProblemConstraints>` is the number of constraints counting
equalities twice. This is because equalities in the input formula are replaced
by two inequalities, where the first inequality is `>=` and the second `<=`.
Afterwards, the `i`-th inequality in the input formula gets `ID := IDmax + i`.

If the constraint count does not match, then the verification fails.

For example if we have the OPB file

```
* #variable= 3 #constraint= 1
1 x1 2 x2 >= 1 ;
1 x3 1 x4  = 1 ;
```

then VeriPB will load the constraints

```
1: 1 x1 2 x2 >= 1 ;
2: 1 x3 1 x4 >= 1 ;
3: -1 x3 -1 x4 >= -1 ;
```

so the following formula check will succeed

```
pseudo-Boolean proof version 3.0
f 3 ;
```

In the past, this rule was used to load the formula into VeriPB. However,
VeriPB loads the full formula right from the start now. So it is only used for
checking that the right number of constraints have been loaded.

### (e) Equals

```
e <OPB style constraint D> : [<ConstraintID for C>] ;
```

Verify that C is the same constraint as D, i.e., has the same degree and
contains the same terms (order of terms does not matter). If the optional
constraint ID of C is not specified, then this rule will check if there exists
the same constraint as D in the database.

It is possible to combine this rule with a label to define a label for the `ConstraintID` of the constraint in the database. This is helpful is it is known that a constraint exists in the database, but its `ConstraintID` is not known. Then we can define the label to map to this constraint. For instance, this looks like:

```
@label e 1 x1 2 x2 3 x3 >= 3 ;
```

### (eobj) Equal Objective

```
eobj <OPB style objective> ;
```

This rule checks if the current objective is equal to the objective given in
the rule. The given objective will be normalized before performing the
comparison with the normalized current objective function. If the check fails,
the proof checking fails.

### (eord_def) and (eord_loaded) Check Order

Sanity-check rules for verifying the current state of orders. For verifying that a rule with a given name is specified correctly

```
eord_def <order name>
  vars
    left <left vars> ;
    right <right vars> ;
    [aux <aux vars> ;]
  end [vars] ;
  [spec
    <OPB constraint> ;
    <OPB constraint> ;
    ...
  end [spec] ;]
  def
    <OPB constraint> ;
    <OPB constraint> ;
    ...
  end [def] ;
end [eord_def] ;
```

The `eord_def` rule can be used to verify that a rule with a given name is specified correctly. So if there is an order defined with the name `<order name>`, then this order has to have the same variables, definition and auxiliary specification as given in this rule. 

```
eord_loaded <order name> <vars>;                  % check the currently loaded order and variables
eord_loaded;                                      % check that no order is currently loaded
```

The `eord_loaded` check what the currently loaded order is.

### (i) Implies

```
i <OPB style constraint D> : [<ConstraintID for C>] ;
```

Verify that C syntactically implies D. I.e., it is possible to derive D from C
by adding literal axioms followed by one saturation step and finally adding
literal axioms for the coefficients in D that are larger than the degree of D.
If the optional constraint ID of C is not specified, then this rule will check
if there exists any constraint in the database that syntactically implies D.

### (ia) Implies and Add

```
ia <OPB style constraint D> : [<ConstraintID for C>] ;
```

Identical to [implies](#i-implies) but also adds the constraint that is implied
to the database with `ConstraintID := IDmax + 1`.

### (setlvl) Set Level

```
setlvl <level> ;
```

This rule does mark all following constraints, up to the next invocation of
this rule, with `<level>`. `<level>` is a non-negative integer. Constraints
which are generated before the first occurrence of this rule are not marked
with any level.

### (wiplvl) Wipe out Level

```
wiplvl <level> ;
```

Delete all constraints (see deletion command) that are marked with `<level>` or
a greater number. Constraints that are not marked with a level can not be
removed with this command.

### Strengthening-to-Core Mode

```
strengthening_to_core on|off
```

This rule enables (`strengthening_to_core on`) or disables
(`strengthening_to_core off`) the strengthening-to-core mode. When enabling the
strengthening-to-core mode, all constraints are moved from the set of derived
constraints to the set of core constraints.

When the strengthening-to-core mode is active, then all constraints introduced
by strengthening rules are added to the set of core constraints instead of the
set of derived constraints. This has the advantage that redundance-based
strengthening only has constraints from the core as proofgoals from the
formula.

## Working with solutions (beyond refutations)

### TLDR;

```
  % log solution
  sol  <literal> <literal> ... ;
  % log solution and add objective-improving constraint
  soli <literal> <literal> ... ;
  soli <literal> <literal> ... : <objective value>;
  % log solution and add solution-excluding constraint
  solx <literal> <literal> ... ;
  % add variable to preserved set
  preserved_add <variable> <OPB constraint> ;
  % remove variable from preserved set
  preserved_rm <variable> <OPB constraint> ;
```

### (sol) Log Solution

```
sol <literal> <literal> ... ;
sol <literal> <literal> ... : <objective value>;
sol x1 ~x2 ;
sol x1 ~x2 : 3;
```

Given a partial assignment in form of a list of `<literal>`, i.e., variable
names with `~` as prefix to indicate negation, check that after unit propagation we are left with an assignment that satisfies all constraints in the database. A constraint is satisfied if the sum of the coefficients for the satisfied literals in the constraint is larger than the right-hand side of the constraint.

If the optional `<objective_value>` hint is provided, it also checks that the provided
`<objective_value>` is achieved by the given assignment.


### (soli) Log Solution and Add Objective-Improving Constraint

```
soli <literal> <literal> ... ;
soli <literal> <literal> ... : <objective value> ;
```

This rule can only be used if the OPB file specifies an objective function
$f(x)$, i.e., it contains a line of the form

```
min: <coefficient> <literal> <coefficient> <literal> ... ;
```
or
```
max: <coefficient> <literal> <coefficient> <literal> ... ;
```

This rule performs the same checks as the [log (sol)ution rule](#sol-log-solution).

If the check is successful then the constraint $f(x) \leq f(\rho) - 1$ is added
with `ConstraintID := IDmax + 1`. If the check is not successful then
verification fails.

### (obji) Log objective value and Add Objective-Improving Constraint

```
obji <objective value> ;
```

Add the constraint $f(x) \leq <objective value>$ with `ConstraintID := IDmax +
1`, without requiring an immediate solution check.

### (solx) Log Solution and Add Solution-Excluding Constraint

```
solx <literal> <literal> ... ;
solx x1 ~x2 ;
```

This rule can only be used if the OPB file specifies a preserved set of variables
$P$, i.e., it contains a line of the form
```
preserved: <variable> <variable> ... ;
```

This rule performs the same checks as the [log (sol)ution rule](#sol-log-solution).

If the check for solution $\rho$ is successful then the clause $\sum_{\{x \in P : \rho(x) = 0\}} x + \sum_{\{x \in P : \rho(x) = 1\}} \overline{x} \geq 1$ is added with `ConstraintID := IDmax +
1`, which consists of the negation of all
literals which are in the preserved set $P$.
Hence, all solutions where the preserved variables are set in the same way
as in the current solution are no longer allowed.


### (preserved_add) Add a Variable to the Preserved Set of Variables

```
preserved_add <variable x> <OPB constraint C> ;
preserved_add x231 1 ~x34 >= 1 ;
```

Add a variable to the preserved set. Adding a variable to the preserved set is
only sound if the possible number of solutions over the preserved set is not
changed. Hence, the rule takes a constraint over preserved variables (i.e.,
constraint can not contain variables that are not preserved).

In a subproof it has to be established that `x <==> C`. This is done using two
proofgoals. The proofgoal `#1` has to establish that `x ==> C` and the
proofgoal `#2` has to establish that `x <== C`, which are both pseudo-Boolean
constraints.

### (preserved_rm) Remove a Variable from the Preserved Set of Variables

```
preserved_rm <variable x> <OPB constraint C> ;
preserved_rm x231 1 ~x34 >= 1 ;
```

Remove a variable from the preserved set. Removing a variable from the
preserved set is only sound if the possible number of solutions over the
preserved set is not changed. Hence, the rule takes a constraint over preserved
variables without the variable `x` (i.e., the constraint C can not contain variables
that are not preserved or `x`).

In a subproof it has to be established that `x <==> C`. This is done using two
proofgoals. The proofgoal `#1` has to establish that `x ==> C` and the
proofgoal `#2` has to establish that `x <== C`, which are both pseudo-Boolean
constraints.

### (epreserved) Check Preserved Set of Variables

```
epreserved <variable> <variable> ... ;
epreserved x1 x3 x42 ;
```

Check that the current preserved set is equal to the specified variables, where the order of variables does not matter.


## Debugging and for Development Only

### TLDR;

```
% add constraint as unchecked assertion
a <OPB style constraint> ;
% track the time of a section
start_time <name> ;
end_time <name> ;
% check if constraint is not in database
is_deleted <OPB style constraint> ;
```

### (a) Unchecked Assertion

```
a <OPB style constraint> ;
a <OPB style constraint> : <ConstraintIds> : <name> : <free-text>;
```

Adds the given constraint without any checks. The constraint gets `ConstraintID
:= IDmax + 1`. Proofs that contain this rule are not valid, because it allows
adding any constraint. For example one could simply add contradiction directly.

This rule is intended to be used during solver development, when not all
aspects of the solver have implemented proof logging, yet. For example, imagine
that the solver knows by some fancy algorithm that it is OK to add a constraint
C, however proof logging for the derivation of C is not implemented yet. Using
this rule we can simply add C without providing a derivation and check with
VeriPB that all other derivations that are already implemented are correct.

Assertions may optionally carry three colon-separated annotation fields — a list
of antecedent constraint IDs, a name, and free-text hints — intended to be read
by external tools; they have no semantic meaning in the main proof format. See
the grammar document for the full syntax.

### Tracking Time to Check Sections of Proof

The following 2 rules can be used to track the time of names sections in the
proof. If there are multiple sections with the same name, then the times are
added up to a total time. The total time is displayed at the end of the
checking when the option `--stats` is used. The `<name>` of a section can be
any string that does not contain a whitespace.

#### (start_time) Start Custom Timer

```
start_time <name> ;
```

Start the timer with the name `<name>`.

**Note:** If the timer `<name>` is already running, then the second start will
be ignored and a warning is printed.

#### (end_time) End Custom Timer

```
end_time <name> ;
```

Stops the timer with the name `<name>` and adds the time that has been elapsed
since the start of the timer to the total time for the timer `<name>`.

**Note:** If a timer is ended that is not running, then the end is ignored and
a warning is printed.

### (is_deleted) Check if a Constraint is Deleted

```
is_deleted <OPB style constraint> ;
```

This rule checks if the given constraint exists in the database. If the
constraint is in the database, the proof will fail. The proof continues
normally if this constraint does not exist in the database.

This rule can be used to double-check that a constraint is truly deleted from
the database maintained by the checker.

### (fail) Fail Proof

```
fail ;
```

This rule immediately fails the proof checking. This rule can be used to fail
proof checking at a certain point if the proof should only be checked until
this point and not further.


# References
[BGMN23]: Bart Bogaerts, Stephan Gocht, Ciaran McCreesh, and Jakob Nordström.
Certified Dominance and Symmetry Breaking for Combinatorial Optimisation.
Journal of Artificial Intelligence Research, 2023.

[GN21]: Stephan Gocht, and Jakob Nordström.
Certifying Parity Reasoning Efficiently Using Pseudo-Boolean Proofs.
Proceedings of the AAAI Conference on Artificial Intelligence, 2021, 35, 3768-3777.

[ABB+26]: Markus Anders, Bart Bogaerts, Benjamin Bogø, Arthur Gontier, Wietze
Koops, Ciaran McCreesh, Magnus O. Myreen, Jakob Nordström, Andy Oertel, Adrian
Rebola-Pardo, Yong Kiam Tan. 2026. “Faster Certified Symmetry Breaking Using
Orders With Auxiliary Variables”. Proceedings of the AAAI Conference on
Artificial Intelligence
40 (17):14140-48.
