 !------------------------------------------------------------------------------
 !  Compile with "elmerf90 SaveBoundaryEnergy.F90 -o obj/SaveBoundaryEnergy"
 !  To check for warnings/debugging also add -fcheck=all -Wall -Wextra -g
 !------------------------------------------------------------------------------
SUBROUTINE SaveBoundaryEnergyComponents(Model,Solver,dt,Transient)
  !------------------------------------------------------------------------------
  USE DefUtils

  IMPLICIT NONE
  !------------------------------------------------------------------------------
  TYPE(Solver_t) :: Solver
  TYPE(Model_t) :: Model
  REAL(KIND=dp) :: dt
  LOGICAL :: Transient
  !------------------------------------------------------------------------------
  TYPE(Variable_t), POINTER :: evar
  TYPE(Element_t), POINTER :: Element
  INTEGER ::i, Active, iMode, NoModes
  CHARACTER(LEN=MAX_NAME_LEN) :: bc_name !, debug_str
  LOGICAL :: Found
  TYPE(Mesh_t), POINTER :: Mesh
  REAL(KIND=dp), ALLOCATABLE :: IntNorm(:), IntTan(:)
  TYPE(ValueList_t), POINTER :: BC
  CHARACTER(*), PARAMETER :: Caller = 'SaveBoundaryEnergyComponents'

  SAVE IntNorm, IntTan, NoModes
  !-------------------------------------------------------------------------------------------

  CALL Info(Caller,'----------------------------------------------------------',Level=6 )
  CALL Info(Caller,'Computing Boundary energy integrals for normal and tangential components of Electric field',Level=4 )

  Mesh => GetMesh()

  NoModes = Model % NumberOfBCs
  ALLOCATE(IntNorm(NoModes), IntTan(NoModes))

  CALL Info(Caller,'Assuming electric field living on nodes')

  evar => VariableGet( Mesh % Variables, 'Electric field e', ThisOnly = .TRUE.)
  IF(.NOT. ASSOCIATED( evar ) ) THEN
    evar => VariableGet( Mesh % Variables, 'Electric field', ThisOnly = .TRUE.)
  END IF
  IF(.NOT. ASSOCIATED(evar) ) THEN
    CALL Fatal(Caller,'Could not find nodal electric field!')
  END IF

  IntNorm = 0.0_dp
  IntTan = 0.0_dp

  ! integration
  Active = GetNOFBoundaryElements()
  DO i=1,Active
    Element => GetBoundaryElement(i)

    iMode = GetBCId( Element )
    IF ( iMode > 0 ) THEN
      BC => Model % BCs(iMode) % Values

      IF (.NOT. ASSOCIATED(BC) ) CYCLE

      Found = .FALSE.
      bc_name = ListGetString(BC, 'Boundary Energy Name', Found )

      IF( Found ) THEN
        CALL LocalIntegBC(Element)
      END IF
    END IF
  END DO

  ! parallel sum
  IF( ParEnv % PEs > 1 ) THEN
    DO i=1,Model % NumberOfBCs
      IntNorm(i) = ParallelReduction(IntNorm(i))
      IntTan(i) = ParallelReduction(IntTan(i))
    END DO
  END IF

  IntNorm = 0.5 * IntNorm
  IntTan = 0.5  * IntTan

  ! save data to be used from other solvers
  DO i=1,Model % NumberOfBCs
    BC => Model % BCs(i) % Values

    IF (.NOT. ASSOCIATED(BC) ) CYCLE

    Found = .FALSE.
    bc_name = ListGetString(BC,'Boundary Energy Name', Found )
    IF( Found ) THEN
      ! Make data available for SaveData / SaveScalars solver
      CALL ListAddConstReal(GetSimulation(), TRIM(bc_name) // "_norm_component", IntNorm(i))
      CALL ListAddConstReal(GetSimulation(), TRIM(bc_name) // "_tan_component", IntTan(i))
    END IF
  END DO

CONTAINS
  !-----------------------------------------------------------------------------
  SUBROUTINE LocalIntegBC(Element)
    !------------------------------------------------------------------------------
    TYPE(Element_t), POINTER :: Element
    !------------------------------------------------------------------------------
    REAL(KIND=dp) :: e_ip(3), e_ip_norm, e_ip_tan(3)
    REAL(KIND=dp), ALLOCATABLE :: Basis(:), e_local(:,:)
    REAL(KIND=dp), ALLOCATABLE :: e_local_parent(:,:), e_local_parentL(:,:), e_local_parentR(:,:)
    REAL(KIND=dp) :: weight, DetJ, Normal(3)
    LOGICAL :: Stat, Found, E_R_zero, E_L_zero
    TYPE(GaussIntegrationPoints_t) :: IP
    INTEGER :: t, i, m, ndofs, n, parent_node_ind, boundary_node_ind
    TYPE(Nodes_t), SAVE :: Nodes
    LOGICAL :: AllocationsDone = .FALSE.
    TYPE(Nodes_t) :: ParentNodesR, ParentNodesL
    TYPE(Element_t), POINTER :: ParentElementR, ParentElementL
    TYPE(ValueList_t), POINTER :: ParentMaterialR, ParentMaterialL
    REAL(KIND=dp) :: epsr_R, epsr_L
    SAVE AllocationsDone,  Basis, e_local, e_local_parent, e_local_parentR, e_local_parentL
    REAL(KIND=dp), PARAMETER :: zero_threshold = 1e-25 ! TODO find a good threshold

    ndofs = evar % dofs
    IF(.NOT. AllocationsDone ) THEN
      m = Mesh % MaxElementDOFs
      ALLOCATE( Basis(m), e_local(ndofs,m), e_local_parent(ndofs,m), &
        e_local_parentR(ndofs,m), e_local_parentL(ndofs,m))
      AllocationsDone = .TRUE.
    END IF

    e_local = 0.0_dp
    e_local_parentR = 0.0_dp
    e_local_parentL = 0.0_dp

    ParentElementR => Element % BoundaryInfo % Right
    ParentElementL => Element % BoundaryInfo % Left

    IF ( .NOT. (ASSOCIATED(ParentElementR) .AND. ASSOCIATED(ParentElementL))) THEN
      CALL FATAL(Caller,'No parent elements found')
    END IF

    CALL GetElementNodes( Nodes, Element )
    n = Element % TYPE % NumberOfNodes

    CALL GetElementNodes( ParentNodesR, ParentElementR )
    CALL GetElementNodes( ParentNodesL, ParentElementL )

    ParentMaterialR => GetMaterial(ParentElementR)
    ParentMaterialL => GetMaterial(ParentElementL)

    Found = .FALSE.
    epsr_R = GetConstReal(ParentMaterialR,'Relative Permittivity', Found)
    IF (.NOT. FOUND) THEN
      CALL FATAL(Caller, 'Did not find R parent permittivity')
    END IF

    Found = .FALSE.
    epsr_L = GetConstReal(ParentMaterialL,'Relative Permittivity', Found)
    IF (.NOT. FOUND) THEN
      CALL FATAL(Caller, 'Did not find L parent permittivity')
    END IF

    e_local_parent = 0.0_dp
    Found = .FALSE.
    CALL GetVectorLocalSolution( e_local_parent, uelement = ParentElementR, uvariable = evar, Found=Found)
    IF (.NOT. FOUND) THEN
      CALL FATAL(Caller, 'Did not find ParentR e-field')
    END IF

    ! Extract e-field from parent element common nodes on the boundary
    outer_loop_R: DO boundary_node_ind=1,n
      Found = .FALSE.
      inner_loop_R: DO parent_node_ind=1, ParentElementR % TYPE % NumberOfNodes
        IF ( ParentElementR % NodeIndexes(parent_node_ind) == Element % NodeIndexes(boundary_node_ind) ) THEN
          e_local_parentR(:, boundary_node_ind) = e_local_parent(:, parent_node_ind)
          Found = .TRUE.
          EXIT inner_loop_R
        END IF
      END DO inner_loop_R
      IF (.NOT. Found) THEN
        CALL FATAL(Caller, 'Did not find a matching node on the parent element (R)')
      END IF
    END DO outer_loop_R

    e_local_parent = 0.0_dp
    Found = .FALSE.
    CALL GetVectorLocalSolution( e_local_parent, uelement = ParentElementL, uvariable = evar, Found=Found)
    IF (.NOT. FOUND) THEN
      CALL FATAL(Caller, 'Did not find ParentL e-field')
    END IF

    outer_loop_L: DO boundary_node_ind=1,n
      Found = .FALSE.
      inner_loop_L: DO parent_node_ind=1, ParentElementL % TYPE % NumberOfNodes
        IF ( ParentElementL % NodeIndexes(parent_node_ind) == Element % NodeIndexes(boundary_node_ind) ) THEN
          e_local_parentL(:, boundary_node_ind) = e_local_parent(:, parent_node_ind)
          Found = .TRUE.
          EXIT inner_loop_L
        END IF
      END DO inner_loop_L
      IF (.NOT. Found) THEN
        CALL FATAL(Caller, 'Did not find a matching node on the parent element (L)')
      END IF
    END DO outer_loop_L

    E_R_zero = SUM(ABS(e_local_parentR(:, 1:n))) < zero_threshold
    E_L_zero = SUM(ABS(e_local_parentL(:, 1:n))) < zero_threshold

    IF ( E_R_zero ) THEN
      IF ( E_L_zero ) THEN
        e_local(:, 1:n) = 0.0_dp
      ELSE
        ! choose E_L
        e_local(:, 1:n) = e_local_parentL(:, 1:n)
      END IF
    ELSE
      IF ( E_L_zero ) THEN
        ! choose E_R
        e_local(:, 1:n) = e_local_parentR(:, 1:n)
      ELSE
        ! choose the one with lower permittivity
        IF (epsr_R < epsr_L) THEN
          e_local(:, 1:n) = e_local_parentR(:, 1:n)
        END IF
        e_local(:, 1:n) = e_local_parentL(:, 1:n)
      END IF
    END IF

    ! Sign of normal vector does not matter as we are only interested in the absolute flux through each element
    Normal = NormalVector(Element, Nodes, Check=.TRUE.)

    ! Numerical integration:
    !-----------------------
    IP = GaussPoints(Element)
    DO t=1,IP % n
      stat = ElementInfo( Element, Nodes, IP % U(t), IP % V(t), &
        IP % W(t), detJ, Basis)
      weight = IP % s(t) * detJ

      DO i=1,3
        e_ip(i) = SUM( Basis(1:n) * e_local(i,1:n) )
      END DO

      e_ip_norm = SUM(e_ip*Normal)
      e_ip_tan = e_ip - e_ip_norm * Normal

      IntNorm(iMode) = IntNorm(iMode) + weight * e_ip_norm*e_ip_norm
      IntTan(iMode) = IntTan(iMode) + weight * SUM(e_ip_tan*e_ip_tan)
    END DO

    !------------------------------------------------------------------------------
  END SUBROUTINE LocalIntegBC
  !------------------------------------------------------------------------------
  !------------------------------------------------------------------------
END SUBROUTINE SaveBoundaryEnergyComponents
 !------------------------------------------------------------------------

