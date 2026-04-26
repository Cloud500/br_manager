"""Validators for committees app."""

from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check."""
    
    is_valid: bool
    message: str = ""


class BetriebsausschussValidator:
    """
    Validator for Betriebsausschuss (Executive Committee) according to § 27 BetrVG.
    
    Validates composition, size, and legal requirements for executive committees.
    """
    
    @staticmethod
    def get_required_additional_members(br_member_count: int) -> int:
        """
        Calculate required number of additional BA members based on BR size.
        
        According to § 27 BetrVG:
        - BR with 9-15 members: 3 additional members
        - BR with 17-23 members: 5 additional members
        - BR with 25-35 members: 7 additional members
        - BR with 37+ members: 9 additional members
        
        Args:
            br_member_count: Number of main committee (Betriebsrat) members
            
        Returns:
            Number of additional members (excluding chair and vice-chair)
            Returns 0 if BR has less than 9 members
        """
        if br_member_count < 9:
            return 0
        elif 9 <= br_member_count <= 15:
            return 3
        elif 16 <= br_member_count <= 16:
            # 16 is gap between ranges
            return 3
        elif 17 <= br_member_count <= 23:
            return 5
        elif 24 <= br_member_count <= 24:
            # 24 is gap between ranges
            return 5
        elif 25 <= br_member_count <= 35:
            return 7
        elif 36 <= br_member_count <= 36:
            # 36 is gap between ranges
            return 7
        else:  # >= 37
            return 9
    
    @staticmethod
    def get_total_ba_size(br_member_count: int) -> int:
        """
        Calculate total BA size including chair and vice-chair.
        
        Args:
            br_member_count: Number of main committee members
            
        Returns:
            Total number of BA members (chair + vice-chair + additional)
        """
        additional = BetriebsausschussValidator.get_required_additional_members(br_member_count)
        if additional == 0:
            return 0
        # Chair + Vice-Chair + additional members
        return 2 + additional
    
    @staticmethod
    def requires_betriebsausschuss(br_member_count: int) -> bool:
        """
        Check if BR is required to form a Betriebsausschuss.
        
        According to § 27 Abs. 1 BetrVG: BR with 9 or more members must form BA.
        
        Args:
            br_member_count: Number of main committee members
            
        Returns:
            True if BA is required, False otherwise
        """
        return br_member_count >= 9
    
    @staticmethod
    def validate_ba_size(
        br_member_count: int,
        ba_member_count: int,
        auto_members_count: int
    ) -> ValidationResult:
        """
        Validate that BA has correct size according to § 27 BetrVG.
        
        Args:
            br_member_count: Number of main committee members
            ba_member_count: Current number of BA members
            auto_members_count: Number of automatically assigned members (chair + vice-chair + auto-roles)
            
        Returns:
            ValidationResult with validity and message
        """
        if not BetriebsausschussValidator.requires_betriebsausschuss(br_member_count):
            return ValidationResult(
                is_valid=True,
                message="BR hat weniger als 9 Mitglieder, kein BA erforderlich"
            )
        
        required_total = BetriebsausschussValidator.get_total_ba_size(br_member_count)
        required_additional = BetriebsausschussValidator.get_required_additional_members(br_member_count)
        
        # Calculate how many additional members we need (excluding auto-members)
        # auto_members includes: chair + vice-chair + roles with auto_include_in_ba
        required_manual_additions = required_total - auto_members_count
        
        if ba_member_count < required_total:
            return ValidationResult(
                is_valid=False,
                message=f"BA zu klein: {ba_member_count}/{required_total} Mitglieder "
                       f"({auto_members_count} automatisch, {required_manual_additions} weitere erforderlich)"
            )
        
        if ba_member_count > required_total:
            return ValidationResult(
                is_valid=False,
                message=f"BA zu groß: {ba_member_count}/{required_total} Mitglieder "
                       f"(maximal {required_total} laut § 27 BetrVG)"
            )
        
        return ValidationResult(
            is_valid=True,
            message=f"BA korrekt besetzt: {ba_member_count} Mitglieder "
                   f"({auto_members_count} automatisch, {required_manual_additions} weitere)"
        )
    
    @staticmethod
    def get_required_size_info(br_member_count: int) -> dict:
        """
        Get detailed information about required BA size.
        
        Args:
            br_member_count: Number of main committee members
            
        Returns:
            Dictionary with size information
        """
        if not BetriebsausschussValidator.requires_betriebsausschuss(br_member_count):
            return {
                'required': False,
                'total_size': 0,
                'additional_members': 0,
                'message': 'Betriebsausschuss nicht erforderlich (BR < 9 Mitglieder)'
            }
        
        additional = BetriebsausschussValidator.get_required_additional_members(br_member_count)
        total = BetriebsausschussValidator.get_total_ba_size(br_member_count)
        
        return {
            'required': True,
            'total_size': total,
            'chair_and_vice': 2,
            'additional_members': additional,
            'message': f'BA erforderlich: {total} Mitglieder (Vorsitz + Stellvertreter + {additional} weitere)'
        }
